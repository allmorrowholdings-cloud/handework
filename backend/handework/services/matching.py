def matching_score(*, text_match, distance_km, radius_km, rating, completion_rate, available, response_minutes=None, risk_score=0):
    """Explainable score. AI semantic similarity may supply text_match; safety and radius remain deterministic."""
    if not available or (distance_km is not None and distance_km > radius_km) or risk_score >= 80:
        return 0.0
    distance_score = max(0.0, 1 - (distance_km / max(radius_km, 1))) if distance_km is not None else 0
    rating_score = min(max(float(rating or 0) / 5, 0), 1)
    completion_score = min(max(float(completion_rate or 0) / 100, 0), 1)
    response_score = 0.5 if response_minutes is None else max(0.0, 1 - min(response_minutes, 1440) / 1440)
    risk_penalty = min(max(risk_score / 100, 0), 1) * 0.2
    score = (float(text_match) * 0.36) + (distance_score * 0.25) + (rating_score * 0.17) + (completion_score * 0.14) + (response_score * 0.08) - risk_penalty
    return round(max(score, 0) * 100, 2)
