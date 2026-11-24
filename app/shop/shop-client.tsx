"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api";

type Product={id:string;name:string;category:string;price:number;image?:string;detail?:string;visual?:"paint"|"masonry"};
type Cart=Record<string,number>;
type CreatedOrder={order:{reference:string;total:number;delivery_fee:number;status:string};authorization_url?:string|null};

function ProductArt({product}:{product:Product}){
  if(product.image) return <img src={product.image} alt=""/>;
  return <div className={`shop-material-art ${product.visual||""}`} aria-hidden="true"><span/><span/><span/></div>;
}

export function ShopClient(){
 const [products,setProducts]=useState<Product[]>([]);
 const [catalogState,setCatalogState]=useState<"loading"|"ready"|"error">("loading");
 const [attempt,setAttempt]=useState(0);
 useEffect(()=>{
   const controller=new AbortController();
   api<{items:Product[]}>("/v1/shop/products",{signal:controller.signal})
     .then(body=>{if(!controller.signal.aborted){setProducts(body.items);setCatalogState("ready");}})
     .catch(()=>{if(!controller.signal.aborted)setCatalogState("error");});
   return ()=>controller.abort();
 },[attempt]);
 const categories=["All",...new Set(products.map(product=>product.category))];
 const [category,setCategory]=useState("All");
 const [cart,setCart]=useState<Cart>(()=>{if(typeof window==="undefined")return {};try{const raw=localStorage.getItem("handework-shop-cart");return raw?JSON.parse(raw):{}}catch{return {}}});
 const [open,setOpen]=useState(false);
 const [checkout,setCheckout]=useState(false);
 const [fulfilment,setFulfilment]=useState<"delivery"|"pickup">("delivery");
 const [notice,setNotice]=useState("");
 const [busy,setBusy]=useState(false);
 const [paymentResult,setPaymentResult]=useState<{reference:string;status:string}|null>(null);

 useEffect(()=>{try{localStorage.setItem("handework-shop-cart",JSON.stringify(cart))}catch{}},[cart]);
 useEffect(()=>{
   const params=new URLSearchParams(window.location.search);
   const reference=params.get("shop_order");
   if(!reference)return;
   api<{order:{reference:string;status:string}}>(`/v1/shop/orders/${encodeURIComponent(reference)}/verify`,{method:"POST"})
     .then(body=>{setPaymentResult({reference:body.order.reference,status:body.order.status});if(body.order.status==="paid")setCart({});})
     .catch(()=>api<{order:{reference:string;status:string}}>(`/v1/shop/orders/${encodeURIComponent(reference)}`)
       .then(body=>setPaymentResult({reference:body.order.reference,status:body.order.status}))
       .catch(()=>setPaymentResult({reference,status:"confirming"})));
 },[]);

 const visible=category==="All"?products:products.filter(p=>p.category===category);
 const count=products.reduce((total,p)=>total+(cart[p.id]||0),0);
 const subtotal=useMemo(()=>products.reduce((sum,p)=>sum+(cart[p.id]||0)*p.price,0),[cart,products]);
 const add=(id:string)=>setCart(c=>({...c,[id]:Math.min(20,(c[id]||0)+1)}));
 const qty=(id:string,n:number)=>setCart(c=>{const next={...c};if(n<=0)delete next[id];else next[id]=Math.min(n,20);return next});

 async function submit(e:FormEvent<HTMLFormElement>){
   e.preventDefault();
   setNotice("");
   setBusy(true);
   const form=new FormData(e.currentTarget);
   try{
     const body=await api<CreatedOrder>("/v1/shop/orders",{
       method:"POST",
       body:JSON.stringify({
         items:products.filter(p=>cart[p.id]).map(p=>({product_id:p.id,quantity:cart[p.id]})),
         fulfilment,
         full_name:String(form.get("name")||""),
         phone:String(form.get("phone")||""),
         email:String(form.get("email")||""),
         area:String(form.get("area")||""),
         address:String(form.get("address")||""),
       })
     });
     if(!body.authorization_url) throw new Error("Payment provider did not return a checkout URL");
     setNotice(`Order ${body.order.reference} created. Opening secure payment…`);
     window.location.assign(body.authorization_url);
   }catch(error){
     const message=error instanceof Error?error.message:"Checkout could not be started";
     setNotice(message.includes("401")?"Sign in as a customer or artisan before checkout.":message);
   }finally{setBusy(false)}
 }

 return <section className="shop-catalog section"><div className="shell">
   {paymentResult&&<div className={`shop-payment-status ${paymentResult.status}`}><strong>{paymentResult.status==="paid"?"Payment confirmed":"Payment is being confirmed"}</strong><span>Order {paymentResult.reference}. {paymentResult.status==="paid"?"Your order is saved and ready for fulfilment.":"If you just paid, your order status will update when payment is confirmed."}</span></div>}
   <div className="shop-toolbar"><div><h2>Shop by craft.</h2><p>Trade tools and equipment available to order.</p></div><button className="shop-cart-button" onClick={()=>setOpen(true)}>Cart <span>{count}</span></button></div>
   {catalogState==="error" ? <p role="status">The catalogue could not load. <button onClick={()=>setAttempt(attempt+1)}>Try again</button></p> : !products.length && <p role="status">{catalogState==="loading"?"Loading the catalogue...":"No supplier-confirmed products are available to order right now."}</p>}
   <div className="shop-category-tabs">{categories.map(c=><button className={category===c?"active":""} onClick={()=>setCategory(c)} key={c}>{c}</button>)}</div>
   <div className="shop-product-grid">{visible.map(p=><article className="shop-product" key={p.id}><div className="shop-product-media"><ProductArt product={p}/></div><div className="shop-product-body"><small>{p.category}</small><h3>{p.name}</h3><p>{p.detail}</p><div className="shop-price"><strong>GHS {p.price.toLocaleString()}</strong></div><button onClick={()=>add(p.id)}>Add to cart</button></div></article>)}</div>
 </div>
 {open&&<div className="shop-drawer-backdrop" onClick={()=>setOpen(false)}><aside className="shop-drawer" onClick={e=>e.stopPropagation()}><div className="shop-drawer-head"><div><span>handEwork shop</span><h2>Your cart.</h2></div><button onClick={()=>setOpen(false)}>×</button></div>{count===0?<div className="shop-empty"><p>Your cart is empty.</p><button onClick={()=>setOpen(false)}>Browse tools</button></div>:<><div className="shop-cart-lines">{products.filter(p=>cart[p.id]).map(p=><div className="shop-cart-line" key={p.id}><div className="shop-cart-thumb"><ProductArt product={p}/></div><div><b>{p.name}</b><span>GHS {p.price.toLocaleString()}</span><div><button onClick={()=>qty(p.id,(cart[p.id]||1)-1)}>−</button><em>{cart[p.id]}</em><button onClick={()=>qty(p.id,(cart[p.id]||0)+1)}>+</button></div></div></div>)}</div><div className="shop-cart-total"><span>Items subtotal</span><strong>GHS {subtotal.toLocaleString()}</strong></div><button className="button button-orange shop-checkout-button" onClick={()=>setCheckout(true)}>Continue to purchase</button></>}</aside></div>}
 {checkout&&<div className="shop-checkout-modal"><form className="shop-checkout-card" onSubmit={submit}><button className="shop-close" type="button" onClick={()=>setCheckout(false)}>×</button><h2>How should we get it to you?</h2><div className="fulfilment-toggle"><label className={fulfilment==="delivery"?"selected":""}><input type="radio" checked={fulfilment==="delivery"} onChange={()=>setFulfilment("delivery")}/>Deliver to me</label><label className={fulfilment==="pickup"?"selected":""}><input type="radio" checked={fulfilment==="pickup"} onChange={()=>setFulfilment("pickup")}/>Pick up at handEwork office</label></div><div className="two-fields"><label>Full name<input required name="name"/></label><label>Phone<input required name="phone" type="tel"/></label></div><label>Email<input required name="email" type="email"/></label>{fulfilment==="delivery"?<><label>Delivery area<input required name="area" placeholder="Area / neighbourhood"/></label><label>Delivery address<textarea required name="address" rows={3}/></label></>:<div className="pickup-note"><b>Office pickup</b><p>Your pickup location and collection window will be confirmed after payment.</p></div>}<div className="shop-cart-total"><span>Items subtotal</span><strong>GHS {subtotal.toLocaleString()}</strong></div><button className="button button-orange" disabled={busy}>{busy?"Starting secure payment…":"Continue to secure payment"}</button>{notice&&<p className="checkout-notice">{notice}</p>}<p className="checkout-login-note">Checkout is available to signed-in customers and artisans. <Link href="/auth/sign-in">Sign in</Link></p></form></div>}
 </section>
}
