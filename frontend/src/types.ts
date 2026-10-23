export interface Branch { id: string; name: string; code: string }
export interface User { id: number; username: string; name: string; roles: string[]; branches: Branch[]; permissions: string[]; branch_permissions?:Record<string,string[]> }
export interface List<T> { results: T[]; count: number }
export interface Patient { id: string; uhid: string; full_name: string; phone: string; date_of_birth: string | null; age: number | null; gender: string; city: string; branch: string; created_at: string }
export interface Appointment { id: string; patient: string; patient_name: string; doctor_name: string; scheduled_at: string; status: string; reason: string; branch: string; version: number }
export interface Bed { id: string; number: string; room_number: string; category: string; status: string; patient_name: string | null; admission_id: string | null; branch: string }
export interface Dashboard { patients_total: number; opd_today: number; active_admissions: number; available_beds: number; appointments_today: number; therapy_pending: number | null }
export interface Platform { organisation: {id: string; name: string}; branches_count: number; staff_count: number; active_staff_count: number; security: {ip_mode: string}; modules: {name: string; status: string}[] }

export type FactorMethod = 'totp'|'backup_code';
export interface MfaPending { code:'mfa_required'; methods:FactorMethod[]; expires_at:string }
export interface SecurityStatus { enabled:boolean; backup_codes_remaining:number; version:number; session_factor_verified_at:string|null; privileged_mfa_required:boolean }
export interface EnrollmentIssued { enrollment_id:string; secret:string; otpauth_uri:string; expires_at:string }
export interface BackupCodesIssued { security:SecurityStatus; backup_codes:string[] }
