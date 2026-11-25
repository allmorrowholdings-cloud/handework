"use client";
import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import type { FormEvent } from "react";
import { api } from "../../../lib/api";

type Product={id:string;name:string;category:string;image?:string|null};
type Media={product_id:string;file_asset_id:string;image_url:string};
export function ShopMediaManager(){
  const [products,setProducts]=useState<Product[]>([]);const [media,setMedia]=useState<Media[]>([]);const [selected,setSelected]=useState("");const [notice,setNotice]=useState("");const [busy,setBusy]=useState(false);
  const load=useCallback(async()=>{const [catalog,files]=await Promise.all([api<{items:Product[]}>('/v1/shop/products'),api<{items:Media[]}>('/v1/admin/shop-media')]);setProducts(catalog.items);setMedia(files.items);setSelected(current=>current||catalog.items[0]?.id||'')},[]);
  useEffect(()=>{let active=true;async function initialLoad(){try{const [catalog,files]=await Promise.all([api<{items:Product[]}>('/v1/shop/products'),api<{items:Media[]}>('/v1/admin/shop-media')]);if(active){setProducts(catalog.items);setMedia(files.items);setSelected(catalog.items[0]?.id||'')}}catch(error){if(active)setNotice(error instanceof Error?error.message:'Shop media could not be loaded')}}void initialLoad();return()=>{active=false}},[]);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=event.currentTarget;const file=new FormData(form).get('file');if(!(file instanceof File)||!file.size)return;setBusy(true);setNotice('');try{await api(`/v1/admin/shop-products/${encodeURIComponent(selected)}/image`,{method:'PUT',body:new FormData(form)});form.reset();setNotice('Shop product image saved.');await load()}catch(error){setNotice(error instanceof Error?error.message:'Image upload failed')}finally{setBusy(false)}}
  async function remove(){const item=media.find(row=>row.product_id===selected);if(!item)return;setBusy(true);setNotice('');try{await api(`/v1/files/${item.file_asset_id}`,{method:'DELETE'});setNotice('Product image removed.');await load()}catch(error){setNotice(error instanceof Error?error.message:'Image could not be removed')}finally{setBusy(false)}}
  const current=media.find(row=>row.product_id===selected);
  return <form className="app-card action-form" onSubmit={submit}><h2>Product images</h2><p>Images are stored in a private bucket and displayed through short-lived signed URLs.</p><label>Product<select required value={selected} onChange={event=>setSelected(event.target.value)}>{products.map(product=><option value={product.id} key={product.id}>{product.name} · {product.category}</option>)}</select></label>{current&&<div><Image src={current.image_url} alt="Selected product" width={220} height={150} unoptimized/><button type="button" className="button ghost-button" disabled={busy} onClick={()=>void remove()}>Remove image</button></div>}<label>Image<input name="file" type="file" accept="image/jpeg,image/png,image/webp" required/></label>{notice&&<p className="data-note" role="status">{notice}</p>}<button className="button button-orange" disabled={busy||!selected}>{busy?'Uploading…':current?'Replace image':'Upload image'}</button></form>
}
