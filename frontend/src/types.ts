export interface Branch { id: string; name: string; code: string }
export interface User { id: number; username: string; name: string; roles: string[]; branches: Branch[]; permissions: string[]; branch_permissions?:Record<string,string[]> }
export interface List<T> { results: T[]; count: number }
export interface Patient { id: string; uhid: string; full_name: string; phone: string; date_of_birth: string | null; age: number | null; gender: string; city: string; branch: string; created_at: string }
export interface Appointment { id: string; patient: string; patient_name: string; doctor_name: string; scheduled_at: string; status: string; reason: string; branch: string; version: number }
export interface Bed { id: string; number: string; room_number: string; category: string; status: string; patient_name: string | null; admission_id: string | null; branch: string }
export interface Dashboard { patients_total: number; opd_today: number; active_admissions: number; available_beds: number; appointments_today: number; therapy_pending: number | null }
export interface Platform { organisation: {id: string; name: string}; branches_count: number; staff_count: number; active_staff_count: number; security: {ip_mode: string; policy_scope?:'effective_deployment'; blocked_addresses_apply?:boolean}; modules: {name: string; status: string}[] }

export type FactorMethod = 'totp'|'backup_code';
export interface MfaPending { code:'mfa_required'; methods:FactorMethod[]; expires_at:string }
export interface SecurityStatus { enabled:boolean; backup_codes_remaining:number; version:number; session_factor_verified_at:string|null; privileged_mfa_required:boolean }
export interface EnrollmentIssued { enrollment_id:string; secret:string; otpauth_uri:string; expires_at:string }
export interface BackupCodesIssued { security:SecurityStatus; backup_codes:string[] }

export interface AuditSummary { id:string; created_at:string; action:string; actor:{id:number;username:string}|null; branch:Branch|null; object_id:string; method:FactorMethod|null }
export interface AuditWindow { after:string; before:string }
export interface AuditPage extends List<AuditSummary> { window:AuditWindow }
export interface AuditSnapshot { name?:string; code?:string; number?:string; room_number?:string; category?:string; status?:string; version?:number; assignments?:{branch:string;role:string}[] }
export interface AuditDetail extends AuditSummary { details:{before?:AuditSnapshot;after?:AuditSnapshot;target_user_id?:number;organisation_id?:string}; details_truncated:boolean; branch_labels:Record<string,Branch>; target:{id:number;username:string}|null }

export interface NetworkPolicy { allowlist_only:boolean; allowlist:string[]; blocklist:string[] }
export interface NetworkPending { change_id:string; status:'pending'|'expired_unreconciled'; activated_at:string; rollback_at:string; activation_revision:number; candidate:NetworkPolicy }
export interface NetworkState { scope:'deployment'; revision:number; owner_organisation:{id:string;name:string}; server_time:string; verified_client_ip:string; confirmed_policy:NetworkPolicy; effective_policy:NetworkPolicy; pending:NetworkPending|null; environment_allows_current_ip:boolean; effective_allows_current_ip:boolean }
export interface NetworkPreview { preview_id:string; base_revision:number; policy:NetworkPolicy; normalisations:{list:'allowlist'|'blocklist';index:number;input:string;canonical:string}[]; current_path:{environment_allows:boolean;candidate_allows:boolean;effective_allows:boolean}; can_activate:boolean; created_at:string; expires_at:string; server_time:string }
export interface NetworkChangeResult { change_id:string; outcome:'pending'|'confirmed'|'reverted'|'expired'|'recovered'|'owner_transferred'; activation_revision:number; revision:number; activated_at:string; rollback_at:string; finished_at:string|null; server_time:string }
export interface NetworkEvent { id:string; created_at:string; action:string; outcome:string; actor:{id:number;username:string}|null; os_actor:string|null; reason:string; change_id:string|null; revision:number; before:NetworkPolicy|null; after:NetworkPolicy|null }
export interface NetworkHistoryPage extends List<NetworkEvent> { window:AuditWindow }
