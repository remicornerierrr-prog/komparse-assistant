(function(){
"use strict";
const dict={
fr:{
"language":"Langue","Komparse Assistant":"Komparse Assistant","Accéder à votre compte":"Accéder à votre compte",
"Déjà inscrit(e) ? Saisissez l'e-mail et le mot de passe de votre compte, puis cliquez sur « Se connecter ». « Créer mon compte » est réservé aux nouvelles inscriptions.":"Déjà inscrit(e) ? Saisissez l'e-mail et le mot de passe de votre compte, puis cliquez sur « Se connecter ». « Créer mon compte » est réservé aux nouvelles inscriptions.",
"Email":"E-mail","Mot de passe":"Mot de passe","Créer mon compte":"Créer mon compte","Se connecter":"Se connecter","Mot de passe oublié ?":"Mot de passe oublié ?",
"Choisir un nouveau mot de passe":"Choisir un nouveau mot de passe","Nouveau mot de passe":"Nouveau mot de passe","Confirmer le nouveau mot de passe":"Confirmer le nouveau mot de passe","Enregistrer le nouveau mot de passe":"Enregistrer le nouveau mot de passe",
"Mon profil":"Mon profil","Prénom":"Prénom","Nom":"Nom","Date de naissance":"Date de naissance","Sexe":"Sexe","Sélectionner":"Sélectionner","Homme":"Homme","Femme":"Femme","Adresse":"Adresse","Ville":"Ville","Types d’annonces à recevoir":"Types d’annonces à recevoir","Annonces nationales":"Annonces nationales","Annonces régionales":"Annonces régionales","Région supplémentaire":"Région supplémentaire","Aucune":"Aucune","NRW":"NRW","NRW inclut les annonces NRW et celles indiquant une ville située dans ce Land.":"NRW inclut les annonces NRW et celles indiquant une ville située dans ce Land.",
"Taille (cm)":"Taille (cm)","Pointure":"Pointure","Taille de vêtements":"Taille de vêtements","Profession":"Profession","Mes photos":"Mes photos","Ajoutez vos 4 photos de profil.":"Ajoutez vos 4 photos de profil.","Enregistrer mon profil":"Enregistrer mon profil","Déconnexion":"Déconnexion","Mes offres":"Mes offres","Retour à mon profil":"Retour à mon profil","À l’affiche pour vous":"À l’affiche pour vous"
},
de:{
"language":"Sprache","Komparse Assistant":"Komparse Assistant","Accéder à votre compte":"Bei deinem Konto anmelden",
"Déjà inscrit(e) ? Saisissez l'e-mail et le mot de passe de votre compte, puis cliquez sur « Se connecter ». « Créer mon compte » est réservé aux nouvelles inscriptions.":"Schon registriert? Gib deine E-Mail-Adresse und dein Passwort ein und klicke auf „Anmelden“. „Konto erstellen“ ist für neue Registrierungen.",
"Email":"E-Mail","Mot de passe":"Passwort","Créer mon compte":"Konto erstellen","Se connecter":"Anmelden","Mot de passe oublié ?":"Passwort vergessen?",
"Choisir un nouveau mot de passe":"Neues Passwort festlegen","Nouveau mot de passe":"Neues Passwort","Confirmer le nouveau mot de passe":"Neues Passwort bestätigen","Enregistrer le nouveau mot de passe":"Neues Passwort speichern",
"Mon profil":"Mein Profil","Prénom":"Vorname","Nom":"Nachname","Date de naissance":"Geburtsdatum","Sexe":"Geschlecht","Sélectionner":"Bitte auswählen","Homme":"Männlich","Femme":"Weiblich","Adresse":"Adresse","Ville":"Stadt","Types d’annonces à recevoir":"Welche Casting-Angebote möchtest du erhalten?","Annonces nationales":"Bundesweite Angebote","Annonces régionales":"Regionale Angebote","Région supplémentaire":"Zusätzliche Region","Aucune":"Keine","NRW":"NRW","NRW inclut les annonces NRW et celles indiquant une ville située dans ce Land.":"NRW umfasst NRW-Angebote sowie Angebote mit einem Drehort in diesem Bundesland.",
"Taille (cm)":"Körpergröße (cm)","Pointure":"Schuhgröße","Taille de vêtements":"Konfektionsgröße","Profession":"Beruf","Mes photos":"Meine Fotos","Ajoutez vos 4 photos de profil.":"Füge deine vier Profilfotos hinzu.","Enregistrer mon profil":"Profil speichern","Déconnexion":"Abmelden","Mes offres":"Meine Angebote","Retour à mon profil":"Zurück zu meinem Profil","À l’affiche pour vous":"Für dich im Casting"
},
en:{
"language":"Language","Komparse Assistant":"Komparse Assistant","Accéder à votre compte":"Sign in to your account",
"Déjà inscrit(e) ? Saisissez l'e-mail et le mot de passe de votre compte, puis cliquez sur « Se connecter ». « Créer mon compte » est réservé aux nouvelles inscriptions.":"Already registered? Enter your email and password, then select “Sign in”. “Create account” is for new registrations.",
"Email":"Email","Mot de passe":"Password","Créer mon compte":"Create account","Se connecter":"Sign in","Mot de passe oublié ?":"Forgot password?",
"Choisir un nouveau mot de passe":"Choose a new password","Nouveau mot de passe":"New password","Confirmer le nouveau mot de passe":"Confirm new password","Enregistrer le nouveau mot de passe":"Save new password",
"Mon profil":"My profile","Prénom":"First name","Nom":"Last name","Date de naissance":"Date of birth","Sexe":"Gender","Sélectionner":"Select","Homme":"Male","Femme":"Female","Adresse":"Address","Ville":"City","Types d’annonces à recevoir":"Casting alerts to receive","Annonces nationales":"Nationwide casting calls","Annonces régionales":"Regional casting calls","Région supplémentaire":"Additional region","Aucune":"None","NRW":"NRW","NRW inclut les annonces NRW et celles indiquant une ville située dans ce Land.":"NRW includes listings tagged NRW and listings with a filming location in this state.",
"Taille (cm)":"Height (cm)","Pointure":"Shoe size","Taille de vêtements":"Clothing size","Profession":"Occupation","Mes photos":"My photos","Ajoutez vos 4 photos de profil.":"Add your four profile photos.","Enregistrer mon profil":"Save my profile","Déconnexion":"Sign out","Mes offres":"My offers","Retour à mon profil":"Back to my profile","À l’affiche pour vous":"Casting calls for you"
}};
function setLanguage(lang){
 const map=dict[lang]||dict.fr;
 document.documentElement.lang=lang;
 document.querySelectorAll("[data-i18n]").forEach(el=>{const k=el.getAttribute("data-i18n");if(map[k])el.textContent=map[k]});
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
 nodes.forEach(n=>{
  const old=n.nodeValue;const trimmed=old.trim();if(!trimmed||!map[trimmed])return;
  n.nodeValue=old.replace(trimmed,map[trimmed]);
 });
 document.querySelectorAll("[placeholder]").forEach(el=>{
  const original=el.dataset.i18nPlaceholder||el.getAttribute("placeholder");el.dataset.i18nPlaceholder=original;
  const placeholders={
   "votre@email.com":{de:"deine@email.de",en:"you@example.com",fr:"votre@email.com"},
   "Votre mot de passe":{de:"Dein Passwort",en:"Your password",fr:"Votre mot de passe"},
   "Ex. Köln":{de:"z. B. Köln",en:"e.g. Cologne",fr:"Ex. Köln"}
  };
  if(placeholders[original])el.placeholder=placeholders[original][lang]||placeholders[original].fr;
 });
 try{localStorage.setItem("komparse-language",lang)}catch(e){}
}
function init(){
 const select=document.getElementById("site-language");if(!select)return;
 let saved="fr";try{saved=localStorage.getItem("komparse-language")||"fr"}catch(e){}
 if(!dict[saved])saved="fr";select.value=saved;
 select.addEventListener("change",()=>{try{localStorage.setItem("komparse-language",select.value)}catch(e){};window.location.reload()});
 setLanguage(saved);
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();