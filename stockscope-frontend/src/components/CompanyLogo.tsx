'use client'

import { useState } from 'react'
import Image from 'next/image'

const sizes = {
  small: 'h-7 w-7 rounded-md text-[10px]',
  medium: 'h-10 w-10 rounded-xl text-xs',
  large: 'h-16 w-16 rounded-2xl text-xl',
}

export default function CompanyLogo({
  symbol,
  size = 'medium',
}: {
  symbol: string
  size?: keyof typeof sizes
}) {
  const ticker = symbol.trim().toUpperCase()
  const [loadedTicker, setLoadedTicker] = useState<string | null>(null)
  const [failedTicker, setFailedTicker] = useState<string | null>(null)
  const loaded = loadedTicker === ticker && failedTicker !== ticker

  return (
    <span
      aria-hidden="true"
      className={`relative flex shrink-0 items-center justify-center overflow-hidden border border-white/[0.08] bg-white/[0.03] font-semibold text-slate-300 ${sizes[size]}`}
    >
      <span className={loaded ? 'invisible' : undefined}>
        {ticker.slice(0, 2)}
      </span>
      {ticker && failedTicker !== ticker && (
        <Image
          key={ticker}
          src={`https://api.elbstream.com/logos/symbol/${encodeURIComponent(ticker)}?format=png&size=128`}
          alt=""
          width={128}
          height={128}
          unoptimized
          loading="lazy"
          referrerPolicy="no-referrer"
          onLoad={() => setLoadedTicker(ticker)}
          onError={() => setFailedTicker(ticker)}
          className={`absolute inset-0 h-full w-full object-contain p-[16%] ${loaded ? 'opacity-100' : 'opacity-0'}`}
        />
      )}
    </span>
  )
}
