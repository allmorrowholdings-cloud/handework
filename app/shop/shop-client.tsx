"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../../lib/api";

type Product={id:string;name:string;category:string;price:number;was:number;image?:string;detail:string;visual?:"paint"|"masonry"};
type Cart=Record<string,number>;
type CreatedOrder={order:{reference:string;total:number;delivery_fee:number;status:string};authorization_url?:string|null};

const products:Product[]=[
  {id:"plumb-kit",name:"Plumber essential kit",category:"Plumbing",price:780,was:950,image:"/services/plumbing.png",detail:"Pipe wrench, basin wrench, cutters, tape, level and fitting essentials."},
  {id:"plumb-pro",name:"Pipe & fitting pro set",category:"Plumbing",price:420,was:510,image:"/services/plumbing.png",detail:"Everyday fitting, sealing and measurement tools for field work."},
  {id:"elec-kit",name:"Electrician safety kit",category:"Electrical",price:690,was:840,image:"/services/electrical.png",detail:"Insulated drivers, tester, meter accessories, gloves and tape."},
  {id:"elec-meter",name:"handEwork digital multimeter",category:"Electrical",price:295,was:360,image:"/services/electrical.png",detail:"Portable voltage, continuity and resistance testing meter."},
  {id:"beauty-kit",name:"Hair professional kit",category:"Hairdressing",price:620,was:760,image:"/services/hair-beauty.png",detail:"Styling tools, brushes, sectioning kit and portable organiser."},
  {id:"makeup-kit",name:"Makeup artist field kit",category:"Makeup",price:540,was:675,image:"/services/makeup.png",detail:"Brush set, palette organiser, hygiene kit, mirror accessories and travel case."},
  {id:"tailor-kit",name:"Tailoring precision kit",category:"Tailoring",price:485,was:590,image:"/services/tailoring.png",detail:"Fabric shears, tape, chalk, seam tools, pins and measuring essentials."},
  {id:"tailor-case",name:"Mobile tailoring tool case",category:"Tailoring",price:230,was:285,image:"/services/tailoring.png",detail:"Organised portable case for field fittings and alterations."},
  {id:"carp-kit",name:"Carpenter measure & finish kit",category:"Carpentry",price:740,was:910,image:"/services/carpentry.png",detail:"Hammer, plane, tape, square, marking and finishing essentials."},
  {id:"carp-measure",name:"handEwork tape & marking set",category:"Carpentry",price:160,was:205,image:"/services/carpentry.png",detail:"Heavy-duty tape, pencils, marking gauge and compact square."},
  {id:"weld-kit",name:"Welder protection & torch kit",category:"Welding",price:890,was:1080,image:"/services/welding.png",detail:"Helmet, gloves, torch accessories, clamps and rod organiser."},
  {id:"weld-glove",name:"Heat-resistant welding gloves",category:"Welding",price:125,was:160,image:"/services/welding.png",detail:"Reinforced work gloves for welding and metal fabrication."},
  {id:"paint-kit",name:"Painter prep & finish kit",category:"Painting",price:465,was:575,visual:"paint",detail:"Rollers, angled brushes, tray, scraper, masking and surface-prep essentials."},
  {id:"paint-pro",name:"Roller, brush & masking set",category:"Painting",price:185,was:230,visual:"paint",detail:"A compact finishing set for residential and commercial touch-ups."},
  {id:"mason-kit",name:"Mason layout & finishing kit",category:"Masonry",price:590,was:720,visual:"masonry",detail:"Trowels, float, line, level, measuring and finishing essentials."},
  {id:"mason-hand",name:"Trowel, float & line set",category:"Masonry",price:210,was:265,visual:"masonry",detail:"Daily hand tools for blockwork, plastering and repair work."},
  {id:"food-kit",name:"Catering service kit",category:"Catering",price:560,was:695,image:"/services/food-events.png",detail:"Service utensils, apron, portable presentation and event essentials."},
  {id:"food-uniform",name:"Chef jacket & apron set",category:"Catering",price:210,was:260,image:"/services/food-events.png",detail:"Branded washable servicewear for catering and events."},
  {id:"digital-kit",name:"Digital creator field kit",category:"Digital & design",price:980,was:1180,image:"/services/digital-design.png",detail:"Compact light, tripod, card reader, cable organiser and creator accessories."},
  {id:"digital-desk",name:"Designer desk essentials",category:"Digital & design",price:320,was:395,image:"/services/digital-design.png",detail:"Tablet stand, cable set, notebook, stylus case and desk organiser."}
];
const categories=["All",...Array.from(new Set(products.map(p=>p.category)))];

function ProductArt({product}:{product:Product}){
  if(product.image) return <img src={product.image} alt=""/>;
  return <div className={`shop-material-art ${product.visual||""}`} aria-hidden="true"><span/><span/><span/></div>;
}

export function ShopClient(){
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
 const count=Object.values(cart).reduce((a,b)=>a+b,0);
 const subtotal=useMemo(()=>products.reduce((sum,p)=>sum+(cart[p.id]||0)*p.price,0),[cart]);
 const add=(id:string)=>setCart(c=>({...c,[id]:(c[id]||0)+1}));
 const qty=(id:string,n:number)=>setCart(c=>{const next={...c};if(n<=0)delete next[id];else next[id]=n;return next});

 async function submit(e:FormEvent<HTMLFormElement>){
   e.preventDefault();
   setNotice("");
   setBusy(true);
   const form=new FormData(e.currentTarget);
   try{
     const body=await api<CreatedOrder>("/v1/shop/orders",{
       method:"POST",
       body:JSON.stringify({
         items:Object.entries(cart).map(([product_id,quantity])=>({product_id,quantity})),
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
   {paymentResult&&<div className={`shop-payment-status ${paymentResult.status}`}><strong>{paymentResult.status==="paid"?"Payment confirmed":"Payment is being confirmed"}</strong><span>Order {paymentResult.reference}. {paymentResult.status==="paid"?"Your order is saved and ready for fulfilment.":"If you just paid, the Paystack webhook will update this automatically."}</span></div>}
   <div className="shop-toolbar"><div><h2>Shop by craft.</h2><p>Discounted handEwork equipment for artisans — also available to customers buying for a team or project.</p></div><button className="shop-cart-button" onClick={()=>setOpen(true)}>Cart <span>{count}</span></button></div>
   <div className="shop-category-tabs">{categories.map(c=><button className={category===c?"active":""} onClick={()=>setCategory(c)} key={c}>{c}</button>)}</div>
   <div className="shop-product-grid">{visible.map(p=><article className="shop-product" key={p.id}><div className="shop-product-media"><ProductArt product={p}/><span>Save {Math.round((1-p.price/p.was)*100)}%</span></div><div className="shop-product-body"><small>{p.category}</small><h3>{p.name}</h3><p>{p.detail}</p><div className="shop-price"><strong>GHS {p.price.toLocaleString()}</strong><s>GHS {p.was.toLocaleString()}</s></div><button onClick={()=>add(p.id)}>Add to cart →</button></div></article>)}</div>
 </div>
 {open&&<div className="shop-drawer-backdrop" onClick={()=>setOpen(false)}><aside className="shop-drawer" onClick={e=>e.stopPropagation()}><div className="shop-drawer-head"><div><span>handEwork shop</span><h2>Your cart.</h2></div><button onClick={()=>setOpen(false)}>×</button></div>{count===0?<div className="shop-empty"><p>Your cart is empty.</p><button onClick={()=>setOpen(false)}>Browse tools</button></div>:<><div className="shop-cart-lines">{products.filter(p=>cart[p.id]).map(p=><div className="shop-cart-line" key={p.id}><div className="shop-cart-thumb"><ProductArt product={p}/></div><div><b>{p.name}</b><span>GHS {p.price.toLocaleString()}</span><div><button onClick={()=>qty(p.id,(cart[p.id]||1)-1)}>−</button><em>{cart[p.id]}</em><button onClick={()=>qty(p.id,(cart[p.id]||0)+1)}>+</button></div></div></div>)}</div><div className="shop-cart-total"><span>Items subtotal</span><strong>GHS {subtotal.toLocaleString()}</strong></div><button className="button button-orange shop-checkout-button" onClick={()=>setCheckout(true)}>Continue to purchase</button></>}</aside></div>}
 {checkout&&<div className="shop-checkout-modal"><form className="shop-checkout-card" onSubmit={submit}><button className="shop-close" type="button" onClick={()=>setCheckout(false)}>×</button><h2>How should we get it to you?</h2><div className="fulfilment-toggle"><label className={fulfilment==="delivery"?"selected":""}><input type="radio" checked={fulfilment==="delivery"} onChange={()=>setFulfilment("delivery")}/>Deliver to me</label><label className={fulfilment==="pickup"?"selected":""}><input type="radio" checked={fulfilment==="pickup"} onChange={()=>setFulfilment("pickup")}/>Pick up at handEwork office</label></div><div className="two-fields"><label>Full name<input required name="name"/></label><label>Phone<input required name="phone" type="tel"/></label></div><label>Email<input required name="email" type="email"/></label>{fulfilment==="delivery"?<><label>Delivery area<input required name="area" placeholder="Area / neighbourhood"/></label><label>Delivery address<textarea required name="address" rows={3}/></label></>:<div className="pickup-note"><b>Office pickup</b><p>Your pickup location and collection window will be confirmed after payment.</p></div>}<div className="shop-cart-total"><span>Items subtotal</span><strong>GHS {subtotal.toLocaleString()}</strong></div><button className="button button-orange" disabled={busy}>{busy?"Starting secure payment…":"Continue to secure payment"}</button>{notice&&<p className="checkout-notice">{notice}</p>}<p className="checkout-login-note">Checkout is available to signed-in customers and artisans. <Link href="/auth/sign-in">Sign in</Link></p></form></div>}
 </section>
}
