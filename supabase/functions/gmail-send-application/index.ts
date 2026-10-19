import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {"Access-Control-Allow-Origin":"https://remicornerierrr-prog.github.io","Access-Control-Allow-Headers":"authorization, apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS","Vary":"Origin"};
function json(data: unknown, status=200) { return new Response(JSON.stringify(data), {status,headers:{...cors,"Content-Type":"application/json"}}); }
function keyBytes(raw:string) { if (/^[0-9a-fA-F]{64}$/.test(raw)) return new Uint8Array(raw.match(/.{2}/g)!.map(x=>parseInt(x,16))); const b=Uint8Array.from(atob(raw),c=>c.charCodeAt(0)); if(b.length!==32) throw new Error("Invalid encryption key"); return b; }
function decode64url(s:string) { const n=s.replaceAll("-","+").replaceAll("_","/"); return Uint8Array.from(atob(n+"=".repeat((4-n.length%4)%4)),c=>c.charCodeAt(0)); }
async function decrypt(value:string,raw:string) { const o=JSON.parse(value); const k=await crypto.subtle.importKey("raw",keyBytes(raw),{name:"AES-GCM"},false,["decrypt"]); const p=await crypto.subtle.decrypt({name:"AES-GCM",iv:decode64url(o.iv)},k,decode64url(o.ciphertext)); return new TextDecoder().decode(p); }
async function encrypt(value:string,raw:string) { const k=await crypto.subtle.importKey("raw",keyBytes(raw),{name:"AES-GCM"},false,["encrypt"]); const iv=crypto.getRandomValues(new Uint8Array(12)); const p=await crypto.subtle.encrypt({name:"AES-GCM",iv},k,new TextEncoder().encode(value)); const enc=(b:Uint8Array)=>{let s="";for(const x of b)s+=String.fromCharCode(x);return btoa(s).replaceAll("+","-").replaceAll("/","_").replaceAll("=","");}; return JSON.stringify({v:1,iv:enc(iv),ciphertext:enc(new Uint8Array(p))}); }
function b64(b:Uint8Array) { let s=""; for(let i=0;i<b.length;i+=32768)s+=String.fromCharCode(...b.subarray(i,i+32768)); return btoa(s); }
function b64url(s:string) { return b64(new TextEncoder().encode(s)).replaceAll("+","-").replaceAll("/","_").replaceAll("=",""); }
function clean(s:string) { return s.replace(/[\r\n]+/g," ").trim(); }
function header(s:string) { return "=?UTF-8?B?"+b64(new TextEncoder().encode(s))+"?="; }
function defaultPhotoName(photoType:string) { return ({portrait:"portrait",left:"blick-links",right:"blick-rechts",full_body:"ganzkoerper"} as Record<string,string>)[photoType]||photoType.replace(/[^a-zA-Z0-9_-]/g,"-"); }
function attachmentFilename(value:unknown,photoType:string,ext:string) {
 const raw=typeof value==="string"?value:"";
 const base=raw.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/\.[^.]*$/,"").replace(/[^a-zA-Z0-9_-]+/g,"-").replace(/^-+|-+$/g,"").slice(0,64);
 return (base||defaultPhotoName(photoType))+"."+ext;
}
function draft(offer:any,p:any) { const name=[p.first_name,p.last_name].filter(Boolean).join(" ").trim(); const date=offer.shoot_date_text||offer.shoot_date||""; const subject=(offer.subject_keyword||"").trim()||(date?"Bewerbung Komparse "+date:"Bewerbung Komparse"); const body=["Hallo,","", "ich möchte mich gerne für den Einsatz als Komparse"+(date?" am "+date:"")+" bewerben.","","Nachfolgend finden Sie meine Angaben:","", "Vollständiger Name: "+name,"Wohnort: "+(p.city||""),"Telefon: "+(p.phone||""),"Geburtsdatum: "+(p.birth_date||""),"Kleidergröße: "+(p.clothing_size||""),"Größe: "+(p.height_cm??"")+" cm","Schuhgröße: "+(p.shoe_size||""),"","Vielen Dank.","","Mit freundlichen Grüßen,",name].join("\n"); return {subject,body}; }
Deno.serve(async(req:Request)=>{
 if(req.method==="OPTIONS") return new Response("ok",{headers:cors});
 if(req.method!=="POST") return json({error:"Method not allowed"},405);
 try {
  const auth=req.headers.get("Authorization"); if(!auth?.startsWith("Bearer ")) return json({error:"Connectez-vous à Komparse."},401);
  const url=Deno.env.get("SUPABASE_URL"), anon=Deno.env.get("SUPABASE_ANON_KEY"), service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"), encKey=Deno.env.get("GMAIL_TOKEN_ENCRYPTION_KEY"), clientId=Deno.env.get("GOOGLE_OAUTH_CLIENT_ID"), clientSecret=Deno.env.get("GOOGLE_OAUTH_CLIENT_SECRET");
  if(!url||!anon||!service||!encKey||!clientId||!clientSecret) return json({error:"Configuration Gmail incomplète."},503);
  const userClient=createClient(url,anon,{global:{headers:{Authorization:auth}},auth:{persistSession:false,autoRefreshToken:false}});
  const {data:u,error:ue}=await userClient.auth.getUser(); if(ue||!u.user) return json({error:"Session expirée. Reconnectez-vous."},401);
  const input=await req.json(), offerId=Number(input.offer_id), action=input.action;
  if(!Number.isSafeInteger(offerId)||offerId<=0) return json({error:"Offre invalide."},400);
  if(action!=="preview"&&action!=="send") return json({error:"Action invalide."},400);
  if(action==="send"&&input.confirm!==true) return json({error:"Confirmation explicite requise."},400);
  const admin=createClient(url,service,{auth:{persistSession:false}});
  const {data:match,error:me}=await admin.from("matches").select("id").eq("user_id",u.user.id).eq("offer_id",offerId).eq("is_active",true).maybeSingle(); if(me)throw me; if(!match)return json({error:"Cette offre ne correspond pas à votre compte."},403);
  const {data:offer,error:oe}=await admin.from("offers").select("id,title,email,subject_keyword,shoot_date,shoot_date_text,admin_review_required,parser_needs_review").eq("id",offerId).maybeSingle(); if(oe)throw oe; if(!offer)return json({error:"Annonce introuvable."},404);
  if(offer.admin_review_required||offer.parser_needs_review)return json({error:"Cette annonce doit être vérifiée avant l'envoi."},422);
  const {data:p,error:pe}=await admin.from("profiles").select("first_name,last_name,phone,birth_date,city,height_cm,shoe_size,clothing_size").eq("id",u.user.id).maybeSingle(); if(pe)throw pe; if(!p)return json({error:"Complétez votre profil avant de candidater."},422);
  const {data:photos,error:ph}=await admin.from("profile_photos").select("photo_type,storage_path").eq("user_id",u.user.id).order("id"); if(ph)throw ph; const profilePhotos=photos||[]; if(profilePhotos.length>10)return json({error:"Votre profil contient plus de 10 photos. Réduisez leur nombre avant de candidater."},422);
  const d=draft(offer,p);
  const {data:connection,error:ce}=await admin.from("gmail_connections").select("*").eq("user_id",u.user.id).maybeSingle(); if(ce)throw ce; if(!connection)return json({error:"Connectez d'abord votre compte Gmail."},422);
  if(action==="preview"){
   const photoPreviews=[];
   for(const photo of profilePhotos){
    const {data:signed,error:se}=await admin.storage.from("profile-photos").createSignedUrl(photo.storage_path,300);
    if(se||!signed?.signedUrl)throw new Error("Photo inaccessible");
    photoPreviews.push({photo_type:photo.photo_type,name:defaultPhotoName(photo.photo_type),url:signed.signedUrl});
   }
   return json({success:true,sender:connection.gmail_email,recipient:offer.email||"",subject:d.subject,body:d.body,photo_previews:photoPreviews});
  }
  const recipient=typeof input.recipient==="string"?input.recipient.trim():"";
  if(recipient.length>254||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient))return json({error:"Saisissez une adresse email valide pour le destinataire."},400);
  if(!Array.isArray(input.photos)||input.photos.length>10)return json({error:"Sélection de photos invalide."},400);
  const selectedPhotos=[];
  const selectedTypes=new Set<string>();
  for(const selection of input.photos){
   if(!selection||typeof selection.photo_type!=="string"||selectedTypes.has(selection.photo_type))return json({error:"Sélection de photos invalide."},400);
   const photo=profilePhotos.find((candidate:any)=>candidate.photo_type===selection.photo_type);
   if(!photo)return json({error:"Une photo sélectionnée n'appartient pas à votre profil."},403);
   selectedTypes.add(selection.photo_type);
   selectedPhotos.push({photo,filename:selection.filename});
  }
  const subject=typeof input.subject==="string"?input.subject.trim():"", emailBody=typeof input.body==="string"?input.body:"";
  if(!subject||subject.length>250||!emailBody.trim()||emailBody.length>12000)return json({error:"Objet ou message invalide."},400);
  if(!Array.isArray(connection.granted_scopes)||!connection.granted_scopes.includes("https://www.googleapis.com/auth/gmail.send"))return json({error:"Autorisation Gmail d'envoi manquante. Reconnectez Gmail."},422);
  const refresh=await decrypt(connection.refresh_token_ciphertext,encKey); let access="";
  if(connection.access_token_ciphertext&&connection.access_token_expires_at&&new Date(connection.access_token_expires_at).getTime()>Date.now()+60000) access=await decrypt(connection.access_token_ciphertext,encKey);
  else {
   const rr=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({client_id:clientId,client_secret:clientSecret,refresh_token:refresh,grant_type:"refresh_token"})});
   const rt=await rr.json(); if(!rr.ok||!rt.access_token)return json({error:"La connexion Gmail doit être renouvelée. Reconnectez Gmail."},422);
   access=rt.access_token; const cipher=await encrypt(access,encKey);
   const {error:save}=await admin.from("gmail_connections").update({access_token_ciphertext:cipher,access_token_expires_at:new Date(Date.now()+Number(rt.expires_in||3600)*1000).toISOString(),updated_at:new Date().toISOString()}).eq("user_id",u.user.id); if(save)throw save;
  }
  const boundary="komparse_"+crypto.randomUUID().replaceAll("-",""), lines=[
   "From: "+header(connection.gmail_email)+" <"+clean(connection.gmail_email)+">","To: <"+clean(recipient)+">","Subject: "+header(subject),"MIME-Version: 1.0",'Content-Type: multipart/mixed; boundary="'+boundary+'"',"","--"+boundary,'Content-Type: text/plain; charset="UTF-8"',"Content-Transfer-Encoding: base64","",b64(new TextEncoder().encode(emailBody))
  ];
  let total=0;
  for(const selection of selectedPhotos){
   const {photo}=selection;
   const {data:blob,error:de}=await admin.storage.from("profile-photos").download(photo.storage_path); if(de||!blob)throw new Error("Photo inaccessible");
   if(!["image/jpeg","image/png","image/webp"].includes(blob.type))return json({error:"Format de photo non autorisé."},422);
   total+=blob.size; if(blob.size>5*1024*1024||total>15*1024*1024)return json({error:"Les photos dépassent la taille totale autorisée de 15 Mo."},413);
   const ext=blob.type==="image/png"?"png":blob.type==="image/webp"?"webp":"jpg", filename=attachmentFilename(selection.filename,photo.photo_type,ext), encoded=b64(new Uint8Array(await blob.arrayBuffer()));
   lines.push("","--"+boundary,"Content-Type: "+blob.type+'; name="'+filename+'"',"Content-Transfer-Encoding: base64",'Content-Disposition: attachment; filename="'+filename+'"',"");
   for(let i=0;i<encoded.length;i+=76)lines.push(encoded.slice(i,i+76));
  }
  lines.push("","--"+boundary+"--","");
  const sent=await fetch("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",{method:"POST",headers:{Authorization:"Bearer "+access,"Content-Type":"application/json"},body:JSON.stringify({raw:b64url(lines.join("\r\n"))}),signal:AbortSignal.timeout(20000)});
  const result=await sent.json().catch(()=>({})); if(!sent.ok){const googleStatus=result?.error?.status||"UNKNOWN"; const googleMessage=String(result?.error?.message||"Erreur Google sans détail").slice(0,400); console.error("Gmail API rejected send",sent.status,googleStatus,googleMessage); return json({error:"Google/Gmail a refusé l’envoi ("+sent.status+" — "+googleStatus+"): "+googleMessage},502);}
  const {error:statusError}=await admin.from("matches").update({application_status:"sent"}).eq("user_id",u.user.id).eq("offer_id",offerId); if(statusError)console.error("Could not update application status",statusError);
  return json({success:true,message_id:result.id,sender:connection.gmail_email,recipient,subject});
 }catch(e){console.error("gmail-send-application error",e);return json({error:"Impossible de traiter la candidature. Réessayez plus tard."},500);}
});