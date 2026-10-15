import { apiClient } from "@/api/client";
import { tokenStorage } from "@/utils/tokens";
import { useAuthStore } from "@/store/authStore";
import { usersApi } from "@/api/usersApi";

type JSONOptions = {challenge: string; user?: {id:string;name:string;displayName:string}; allowCredentials?: {id:string;type:PublicKeyCredentialType}[]; excludeCredentials?: {id:string;type:PublicKeyCredentialType}[]; [key:string]:unknown};
function decode(value:string): ArrayBuffer {
  const bytes=Uint8Array.from(atob(value.replace(/-/g,"+").replace(/_/g,"/")),char=>char.charCodeAt(0));
  return bytes.buffer;
}
function encode(value:ArrayBuffer | null) {
  return value === null ? null : btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
}
export function passkeysSupported() { return typeof window !== "undefined" && window.isSecureContext && typeof PublicKeyCredential !== "undefined"; }
function checked() {if (!passkeysSupported()) throw new Error("This browser cannot use passkeys here. Use a supported browser on the secure site, or sign in with email verification.");}
function serialize(credential:Credential | null) {
 if (!credential || !(credential instanceof PublicKeyCredential)) throw new Error("Passkey verification was cancelled. You can try again or use email verification.");
 const response=credential.response;
 const base={id:credential.id,rawId:encode(credential.rawId),type:credential.type,response:{clientDataJSON:encode(response.clientDataJSON)}};
 if (response instanceof AuthenticatorAttestationResponse) return {...base,response:{...base.response,attestationObject:encode(response.attestationObject),transports:response.getTransports()}};
 const assertion=response as AuthenticatorAssertionResponse;
 return {...base,response:{...base.response,authenticatorData:encode(assertion.authenticatorData),signature:encode(assertion.signature),userHandle:encode(assertion.userHandle)}};
}
export async function enrollPasskey(name:string,password:string) {
 checked();
 const {data}=await apiClient.post<{challenge_id:string;options:JSONOptions}>("security/passkeys/register/options/",{name,password});
 const o=data.options;
 const publicKey={...o,challenge:decode(o.challenge),user:{...o.user!,id:decode(o.user!.id)},excludeCredentials:o.excludeCredentials?.map(key=>({...key,id:decode(key.id)}))} as PublicKeyCredentialCreationOptions;
 const credential=serialize(await navigator.credentials.create({publicKey}));
 await apiClient.post("security/passkeys/register/verify/",{challenge_id:data.challenge_id,credential});
}
export async function signInWithPasskey(email:string,password:string,remember:boolean) {
 checked();
 const {data}=await apiClient.post<{challenge_id:string;options:JSONOptions}>("auth/passkey/options/",{email,password});
 const o=data.options;
 const publicKey={...o,challenge:decode(o.challenge),allowCredentials:o.allowCredentials?.map(key=>({...key,id:decode(key.id)}))} as PublicKeyCredentialRequestOptions;
 const credential=serialize(await navigator.credentials.get({publicKey}));
 const verified=await apiClient.post<{access:string;refresh:string}>("auth/passkey/verify/",{challenge_id:data.challenge_id,credential});
 tokenStorage.setTokens(verified.data.access,verified.data.refresh,remember);
 try { const user=await usersApi.me();useAuthStore.getState().setUser(user);return user; }
 catch (error) {tokenStorage.clear();useAuthStore.getState().setUser(null);throw error;}
}
