'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, saveAuthSession, rememberDevice, requestDeviceSession } from '@/lib/api'
import AnimatedAction from './ui/AnimatedAction'

export default function LoginForm({ onLoginSuccess }: { onLoginSuccess: () => void }) {
  const [remember, setRemember] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [ownerPassword, setOwnerPassword] = useState('')
  const [token, setToken] = useState('')
  const [reset, setReset] = useState(false)
  const [setup, setSetup] = useState(false)
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    setRemember(window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 12000)
    const fragment = new URLSearchParams(window.location.hash.slice(1))
    setToken(fragment.get('invite') || '')
    setReset(fragment.get('reset') === '1')
    void fetch(`${API_BASE_URL}/api/auth/config`, { signal: controller.signal, cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('The workspace is temporarily unavailable. Please retry shortly.')
        const config = await response.json()
        setSetup(config.setup_required)
        setReady(true)
        setError('')
      }).catch(() => setError('Cannot reach the private workspace. Please retry shortly.'))
      .finally(() => clearTimeout(timer))
    return () => { clearTimeout(timer); controller.abort() }
  }, [retry])
  const joining = setup || !!token
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const response = await requestDeviceSession(token ? 'accept-invite' : setup ? 'setup' : 'sign-in', {
        email, name: reset ? 'Account' : name, password, token, owner_password: ownerPassword, remember_device: remember,
      })
      const body = await response.json()
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Please check the form and try again.')
      if (token) window.history.replaceState(null, '', window.location.pathname)
      rememberDevice(response.headers.get('X-StockScope-Remembered') === '1')
      saveAuthSession(body)
      setPassword(''); setOwnerPassword('')
      onLoginSuccess()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Sign-in failed. Please retry.') }
    finally { setBusy(false) }
  }
  return <main className="pwa-auth flex min-h-dvh items-center justify-center bg-[#111613] px-6 py-12">
    <div className="w-full max-w-md">
      <p className="text-xs uppercase tracking-[0.22em] text-[#b6c8ab]">Private research desk</p>
      <h1 className="mt-4 font-serif text-5xl tracking-tight text-[#f1eee5]">StockScope.</h1>
      <p className="mt-4 text-sm leading-6 text-slate-400">A quiet place to follow companies, keep your ideas, and study the evidence.</p>
      <form onSubmit={submit} className="mt-10 space-y-5 rounded-xl border border-white/10 bg-white/[0.02] p-6">
        <h2 className="text-lg text-slate-100">{reset ? 'Reset your password' : token ? 'Accept your invitation' : setup ? 'Set up your owner account' : 'Welcome back'}</h2>
        {joining && !reset && <label className="block text-sm text-slate-300">Your name<input required maxLength={80} autoComplete="name" value={name} onChange={e => setName(e.target.value)} className="field-input mt-2 w-full" /></label>}
        <label className="block text-sm text-slate-300">Email<input required type="email" autoComplete="username" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} className="field-input mt-2 w-full" /></label>
        <label className="block text-sm text-slate-300">{joining ? 'Choose a password' : 'Password'}<input required type="password" minLength={joining ? 12 : 1} maxLength={128} autoComplete={joining ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} className="field-input mt-2 w-full" />{joining && <span className="mt-2 block text-xs text-slate-500">At least 12 characters. A long passphrase works well.</span>}</label>
        {setup && !token && <label className="block text-sm text-slate-300">Existing owner access password<input required type="password" autoComplete="off" value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)} className="field-input mt-2 w-full" /><span className="mt-2 block text-xs leading-5 text-slate-500">Used once to create the first account. Shared-password access ends after setup.</span></label>}
        <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-slate-300">
          <input type="checkbox" checked={remember} onChange={event => setRemember(event.target.checked)} className="h-4 w-4 accent-[#b6c8ab]" />
          Keep me signed in on this device for 30 days
        </label>
        {error && <p role="alert" className="text-sm leading-6 text-amber-200">{error}</p>}
        {!ready && error ? <AnimatedAction type="button" onClick={() => setRetry(value => value + 1)} className="button-secondary w-full">Retry connection</AnimatedAction> : <AnimatedAction type="submit" disabled={!ready || busy} className="min-h-11 w-full rounded-lg bg-[#b6c8ab] px-4 py-3 text-sm font-medium text-[#111613] disabled:opacity-50">{busy ? 'Please wait…' : !ready ? 'Connecting…' : reset ? 'Reset password' : joining ? 'Create account' : 'Sign in'}</AnimatedAction>}
      </form>
      <p className="mt-6 text-center text-xs leading-6 text-slate-500">Invitation only · No subscriptions<br />Need access or help signing in? Contact the workspace owner.</p>
    </div>
  </main>
}
