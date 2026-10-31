'use client'
import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import AppShell from '@/components/AppShell'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import { workspaceRequest } from '@/hooks/useLists'
import { getAuthSession } from '@/lib/api'
import Link from 'next/link'

type Member = { id: string; name: string; email: string; role: string; active: boolean }
type Invitation = { id: string; email: string; role: string; expires_at: string }
type Usage = {
  provider: string; used: number; limit: number | null; blocked_until?: number; unit?: string
  operations?: Record<string, number>; categories?: Record<string, number>; responses?: Record<string, number>
  unattributed?: number; history?: { day: string; count: number; responses: Record<string, number> }[]
}
const counts = (values?: Record<string, number>) => Object.entries(values ?? {}).map(([key, count]) => `${key}: ${count}`).join(' · ') || 'None recorded'

function UsageDetails({ value }: { value: Usage }) {
  return <div className="mt-3 space-y-2 text-xs leading-5 text-slate-400">
    {!!value.blocked_until && value.blocked_until * 1000 > Date.now() && <p className="text-amber-200">Cooling down until {new Date(value.blocked_until * 1000).toLocaleString()}</p>}
    <details><summary className="cursor-pointer">Usage details · {value.unit ?? 'requests'}</summary>
      <p className="mt-2">Operations: {counts(value.operations)}</p>
      <p>Request types: {counts(value.categories)}</p>
      <p>Responses: {counts(value.responses)}</p>
      {(value.unattributed ?? 0) > 0 && <p>Earlier requests without attribution: {value.unattributed}</p>}
      <p className="mt-3">Recorded history (last 30 UTC days)</p>
      {value.history?.length ? <ul>{value.history.map(day => <li key={day.day}>{day.day}: {day.count} {value.unit ?? 'requests'} · {counts(day.responses)}</li>)}</ul> : <p>No previous days recorded yet.</p>}
    </details>
  </div>
}
export default function AccessPage() {
  const session = getAuthSession()
  const enabled = session?.role === 'admin' && !!session.user
  const client = useQueryClient()
  const access = useQuery<{ users: Member[]; invites: Invitation[] }>({ queryKey: ['access'], queryFn: () => workspaceRequest('/api/access'), enabled })
  const usage = useQuery<{ providers: Usage[] }>({ queryKey: ['resources'], queryFn: () => workspaceRequest('/api/resources'), enabled, staleTime: 60_000, refetchInterval: 60_000 })
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')
  const [link, setLink] = useState('')
  const [copied, setCopied] = useState(false)
  const action = useMutation({ mutationFn: ({ path, method, body }: { path: string; method: string; body?: unknown }) => workspaceRequest(path, method, body), onSuccess: () => client.invalidateQueries({ queryKey: ['access'] }) })
  const invite = async (event: FormEvent) => {
    event.preventDefault(); setCopied(false); setLink('')
    try { const result = await action.mutateAsync({ path: '/api/access/invites', method: 'POST', body: { email, role } }); setLink(`${window.location.origin}/#invite=${encodeURIComponent(result.token)}`); setEmail('') } catch {}
  }
  return <AppShell><h1 className="font-serif text-3xl">Workspace access</h1><p className="mt-3 text-sm leading-6 text-slate-400">A small, private research circle. You choose who can join.</p>
    {!enabled ? <p className="mt-8 text-sm text-amber-200">{session?.role === 'admin' ? <Link href="/account">Set up your owner account to invite friends →</Link> : 'Only an administrator can manage access.'}</p> : <>
      <form onSubmit={invite} className="surface my-8 p-6"><h2 className="font-medium">Invite a friend</h2><p className="mt-2 text-xs leading-6 text-slate-500">Create a single-use link and share it privately with this person. It expires in three days. No email is sent automatically.</p><div className="mt-5 flex flex-wrap items-end gap-3"><label className="min-w-0 flex-1 text-xs text-slate-400">Their email<input required type="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} className="field-input mt-2 block w-full" /></label><label className="text-xs text-slate-400">Access<AnimatedSelect aria-label="Invitation role" value={role} onValueChange={setRole} className="field-input mt-2"><option value="member">Member</option><option value="viewer">Read-only research</option><option value="admin">Administrator</option></AnimatedSelect></label><button className="button-secondary" disabled={action.isPending}>Create invitation</button></div>
        {link && <div className="mt-5 rounded-lg border border-[#b6c8ab]/20 p-4"><label className="text-xs text-slate-400">Private invitation or password reset link<input readOnly value={link} className="field-input mt-2 block w-full text-xs" onFocus={e => e.target.select()} /></label><button type="button" className="mt-3 text-xs text-[#b6c8ab]" onClick={async () => { try { await navigator.clipboard.writeText(link); setCopied(true) } catch { setCopied(false) } }}>{copied ? 'Copied' : 'Copy link'}</button></div>}
      </form>
      {action.error && <p role="alert" className="mb-5 text-sm text-amber-200">{action.error.message}</p>}
      {access.isError && <p role="alert" className="text-sm text-amber-200">Access records could not be loaded. <button onClick={() => void access.refetch()} className="underline">Retry</button></p>}
      {access.isPending && <p role="status" className="text-sm text-slate-400">Loading members…</p>}
      <section className="surface divide-y divide-white/10"><h2 className="p-5 font-medium">Members</h2>{access.data?.users.map(user => <div key={user.id} className="flex flex-wrap items-center gap-4 p-5"><div className="min-w-0 flex-1"><p className="text-sm">{user.name}{user.id === session.user?.id && ' (you)'}</p><p className="mt-1 break-all text-xs text-slate-500">{user.email} · {user.active ? 'Active' : 'Suspended'}</p></div>{user.active && <button disabled={action.isPending} className="text-xs text-slate-400" onClick={async () => { try { const result = await action.mutateAsync({ path: `/api/access/users/${user.id}/reset`, method: 'POST' }); setLink(`${window.location.origin}/#invite=${encodeURIComponent(result.token)}&reset=1`); setCopied(false); window.scrollTo({ top: 0, behavior: 'smooth' }) } catch {} }}>Password reset link</button>}<AnimatedSelect aria-label={`Role for ${user.email}`} value={user.role} disabled={action.isPending || user.id === session.user?.id} onValueChange={value => action.mutate({ path: `/api/access/users/${user.id}`, method: 'PUT', body: { role: value, active: user.active } })} className="field-input text-xs"><option value="admin">Administrator</option><option value="member">Member</option><option value="viewer">Read-only research</option></AnimatedSelect>{user.id !== session.user?.id && <button disabled={action.isPending} className="button-secondary text-xs" onClick={() => action.mutate({ path: `/api/access/users/${user.id}`, method: 'PUT', body: { active: !user.active, role: user.role } })}>{user.active ? 'Suspend access' : 'Restore access'}</button>}</div>)}</section>
      {!!access.data?.invites.length && <section className="surface mt-6 p-5"><h2 className="font-medium">Pending invitations</h2>{access.data.invites.map(value => <div key={value.id} className="mt-4 flex flex-wrap justify-between gap-3 text-xs"><p className="break-all text-slate-400">{value.email} · expires {new Date(value.expires_at).toLocaleDateString()}</p><button disabled={action.isPending} className="text-amber-200" onClick={() => action.mutate({ path: `/api/access/invites/${value.id}`, method: 'DELETE' })}>Revoke invitation</button></div>)}</section>}
      <section className="surface mt-6 p-5">
        <h2 className="font-medium">Shared resource usage</h2>
        <p className="mt-2 text-xs leading-6 text-slate-500">Counts reset at midnight UTC. Yahoo counts include authentication and retries. When a provider asks us to slow down, the workspace pauses requests and keeps saved research available.</p>
        {usage.isError && <p className="mt-4 text-xs text-amber-200">Usage is temporarily unavailable.</p>}
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {usage.data?.providers.map(value => (
            <div key={value.provider}>
              <div className="flex justify-between text-xs">
                <span className="capitalize text-slate-400">{value.provider}</span>
                <span className="tabular-nums text-slate-300">
                  {value.limit === null ? `${value.used} requests · No daily app cap` : value.limit === 0 ? 'Disabled' : `${value.used} / ${value.limit}`}
                </span>
              </div>
              {value.limit !== null && value.limit > 0 && <div className="mt-2 h-1 rounded bg-white/5"><div className="h-1 rounded bg-[#b6c8ab]" style={{ width: `${Math.min(100, value.used / value.limit * 100)}%` }} /></div>}
              <UsageDetails value={value} />
            </div>
          ))}
        </div>
      </section>
    </>}
  </AppShell>
}
