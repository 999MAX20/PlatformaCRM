import {apiClient} from "./client";
export type AssistanceScope={business_id:number;patient_id:number;encounter_id:number;expected_revision:number;field:string};
export type AssistanceSuggestion={text:string;receipt:string;field:string;revision:number};
export const medicalAssistanceApi={
 dictate:async(scope:AssistanceScope,text:string,audio:Blob,language:string,signal?:AbortSignal)=>{
  const form=new FormData();Object.entries({...scope,text,language}).forEach(([key,value])=>form.append(key,String(value)));form.append("audio",audio,"dictation.wav");
  return(await apiClient.post<AssistanceSuggestion>("/api/medical/assistance/dictation/",form,{signal,headers:{"Content-Type":"multipart/form-data"}})).data;
 },
 suggest:async(scope:AssistanceScope,text:string,signal?:AbortSignal)=>(await apiClient.post<AssistanceSuggestion>("/api/medical/assistance/suggest/",{...scope,text},{signal})).data,
 accept:async(scope:AssistanceScope,text:string,suggestion:AssistanceSuggestion,signal?:AbortSignal)=>(await apiClient.post<{text:string;field:string;revision:number}>("/api/medical/assistance/accept/",{...scope,text,suggestion:suggestion.text,receipt:suggestion.receipt},{signal})).data,
};
