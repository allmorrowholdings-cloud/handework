import hashlib
import hmac
import os
import secrets

from redis import Redis

from .arkesel import send_sms, sms_enabled
from .phone_otp import otp_enabled


def verification_enabled():
    return otp_enabled() and sms_enabled()


def connection():
    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("Verification storage unavailable")
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3
    )


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def challenge_key(user_id):
    return "handework:otp:challenge:" + digest(user_id)


def code_hash(user_id, phone, code):
    secret = os.getenv("SECRET_KEY", "")
    if len(secret) < 32 or secret.startswith("development"):
        raise RuntimeError("Secure verification key unavailable")

    value = f"handework:phone:{user_id}:{phone}:{code}"

    return hmac.new(
        secret.encode(),
        value.encode(),
        hashlib.sha256
    ).hexdigest()


RESERVE = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    return 0
end

for i = 2, 4 do
    local maximum = 3
    if i == 4 then maximum = 30 end
    if tonumber(redis.call('GET', KEYS[i]) or '0') >= maximum then
        return 0
    end
end

redis.call('SET', KEYS[1], '1', 'EX', 60)

for i = 2, 4 do
    local n = redis.call('INCR', KEYS[i])
    if n == 1 then
        local ttl = 3600
        if i == 4 then ttl = 86400 end
        redis.call('EXPIRE', KEYS[i], ttl)
    end
end

redis.call('HSET', KEYS[5],
    'hash', ARGV[1],
    'attempts', '0'
)
redis.call('EXPIRE', KEYS[5], 300)

return 1
"""


VERIFY = """
local stored = redis.call('HGET', KEYS[1], 'hash')
if not stored then return 0 end

local attempts = redis.call('HINCRBY', KEYS[1], 'attempts', 1)

if stored == ARGV[1] and attempts <= 5 then
    redis.call('DEL', KEYS[1])
    return 1
end

if attempts >= 5 then
    redis.call('DEL', KEYS[1])
end

return 0
"""


def request_code(user_id, phone):
    if not verification_enabled():
        raise RuntimeError("Phone verification disabled")

    if not phone.startswith("+233"):
        raise ValueError("Only Ghanaian numbers are supported")

    code = f"{secrets.randbelow(1000000):06d}"
    signature = code_hash(user_id, phone, code)

    keys = [
        "handework:otp:cooldown:" + digest(user_id),
        "handework:otp:user:" + digest(user_id),
        "handework:otp:phone:" + digest(phone),
        "handework:otp:global",
        challenge_key(user_id)
    ]

    with connection() as client:
        reserved = client.eval(
            RESERVE, len(keys), *keys, signature
        )

    if reserved != 1:
        return False

    send_sms(
        phone,
        f"Your handEwork verification code is {code}. "
        "It expires in 5 minutes. Do not share it."
    )

    return True


def confirm_code(user_id, phone, code):
    if not verification_enabled():
        return False

    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return False

    signature = code_hash(user_id, phone, code)

    with connection() as client:
        return client.eval(
            VERIFY,
            1,
            challenge_key(user_id),
            signature
        ) == 1


def invalidate_code(user_id):
    with connection() as client:
        client.delete(challenge_key(user_id))
