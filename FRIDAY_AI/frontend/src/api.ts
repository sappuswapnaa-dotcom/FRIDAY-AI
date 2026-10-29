export async function request<T>(path:string, init:RequestInit={}):Promise<T> {
  const response=await fetch(path,{...init,headers:{...(init.body && !(init.body instanceof FormData)?{'Content-Type':'application/json'}:{}),...(init.headers||{})}});
  if(!response.ok){let detail=`Request failed (${response.status})`;try{const data=await response.json();detail=data.detail||detail}catch{}throw new Error(detail)}
  if(response.status===204)return undefined as T;
  return response.json() as Promise<T>;
}
export const json=(value:unknown)=>JSON.stringify(value);
export interface Metrics {platform:string;platform_release:string;cpu_percent:number;ram_percent:number;ram_used_gb:number;ram_total_gb:number;battery_percent:number|null;battery_plugged:boolean|null;network_interface_up:boolean;network_interfaces:string[]}
export interface ModelState {online:boolean;models:string[];selected:string|null;error:string|null}
export interface VoiceStatus {whisper_ready:boolean;whisper_package:boolean;whisper_model:boolean;piper_ready:boolean;piper_executable:boolean;piper_voices:string[];whisper_path:string}
export interface Status {backend:string;mode:string;metrics:Metrics;ollama:ModelState;voice:VoiceStatus;windows_control_available:boolean;workspace:string;active_task:{id:string;status:string;conversation_id:string}|null}
export interface Conversation {id:string;title:string;created_at:string;updated_at:string}
export interface Message {role:'user'|'assistant';content:string;created_at?:string}
export interface Action {id:number;task_id:string;name:string;arguments:Record<string,unknown>;status:string;detail:string;created_at:string}
export interface Memory {id:string;category:string;name:string;value:string;updated_at:string}
export interface Schedule {id:string;kind:string;label:string;payload:{path?:string};next_run:string;repeat_mode:string;enabled:boolean;last_result:string|null}
export interface Approval {approval_id:string;tool:string;reason:string;arguments:Record<string,unknown>;page:string|null;target?:Record<string,unknown>|null}
