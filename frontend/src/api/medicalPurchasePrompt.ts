import {apiClient} from "./client";
export type PurchasePromptScope={business_id:number;encounter_id:number};
export type PurchasePromptClaim={show:boolean;token?:string;branch?:{id:number;name:string}};
export const medicalPurchasePromptApi={
 claim:async(scope:PurchasePromptScope,signal?:AbortSignal)=>(await apiClient.post<PurchasePromptClaim>("/api/medical/purchase-prompts/claim/",scope,{signal})).data,
 decide:async(business_id:number,token:string,decision:"ack"|"yes"|"no")=>(await apiClient.post("/api/medical/purchase-prompts/decision/",{business_id,token,decision})).data,
};
