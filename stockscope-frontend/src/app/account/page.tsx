'use client'
import { useState, type FormEvent } from 'react'
import AppShell from '@/components/AppShell'
import LoginForm from '@/components/LoginForm'
import { clearAuthSession, getAuthSession } from '@/lib/api'
import { workspaceRequest } from '@/hooks/useLists'
export default function AccountPage() {
  const session = getAuthSession()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const change = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await workspaceRequest('/api/auth/password', 'POST', { current_password: currentPassword, new_password: newPassword }); clearAuthSession() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Password could not be changed.') }
    finally { setBusy(false) }
  }
  if (!session?.user) return <LoginForm onLoginSuccess={() => window.location.assign('/')} />
  return <AppShell><h1 className="font-serif text-3xl">Your account</h1><p className="mt-3 text-sm text-slate-400">{session.user.name} · {session.user.email}</p><form onSubmit={change} className="surface mt-8 max-w-md space-y-5 p-6"><h2 className="font-medium">Change password</h2><label className="block text-sm text-slate-400">Current password<input type="password" required autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} className="field-input mt-2 w-full" /></label><label className="block text-sm text-slate-400">New password<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} className="field-input mt-2 w-full" /></label><p className="text-xs leading-6 text-slate-500">Use at least 12 characters. Changing your password signs out all your current sessions.</p>{error && <p role="alert" className="text-sm text-amber-200">{error}</p>}<button disabled={busy} className="button-secondary">{busy ? 'Saving…' : 'Change password'}</button></form></AppShell>
}
