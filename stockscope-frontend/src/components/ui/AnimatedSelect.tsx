'use client'

import { Children, isValidElement, type ReactNode, type ComponentPropsWithoutRef } from 'react'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'
import * as Select from '@animate-ui/react/primitives/radix-ui/select'
import { twMerge } from 'tailwind-merge'

type OptionProps = { value?: string; children?: ReactNode; disabled?: boolean }
interface AnimatedSelectProps extends Omit<ComponentPropsWithoutRef<'button'>, 'value' | 'onChange' | 'defaultValue'> {
  value: string
  onValueChange: (value: string) => void
  children: ReactNode
  name?: string
  required?: boolean
}
function optionText(children: ReactNode): string {
  return Children.toArray(children).map(child => isValidElement<OptionProps>(child) ? optionText(child.props.children) : String(child)).join('')
}

/** Styled Animate UI select; retains existing option labels and empty-value choices. */
export default function AnimatedSelect({ value, onValueChange, children, className, disabled, name, required, ...props }: AnimatedSelectProps) {
  const options = Children.toArray(children).filter(isValidElement<OptionProps>).map(option => ({
    value: option.props.value ?? optionText(option.props.children),
    label: optionText(option.props.children),
    disabled: option.props.disabled,
  }))
  // Radix reserves the empty string for placeholders. Prefix every value so an
  // explicit “All” / “Unlabelled” option remains a selectable, reversible choice.
  const encode = (value: string) => `option:${value}`
  return (
    <Select.Root value={required && !value ? '' : encode(value)} onValueChange={next => onValueChange(next.slice(7))} disabled={disabled} name={name} required={required}>
      <Select.Trigger {...props} className={twMerge('animated-select flex min-h-11 w-full items-center justify-between gap-3 rounded-lg border border-white/10 bg-[#101218] px-3 py-2.5 text-left text-sm text-slate-200 shadow-sm transition-colors hover:border-violet-400/40 focus-visible:border-violet-400 disabled:cursor-not-allowed disabled:opacity-50', className, 'flex')}>
        <span className="min-w-0 truncate"><Select.Value placeholder={options.find(option => !option.value)?.label} /></span>
        <Select.Icon asChild><ChevronDown aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400" /></Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content position="popper" sideOffset={6} collisionPadding={12} className="z-[100] max-h-[min(20rem,var(--radix-select-content-available-height))] w-[var(--radix-select-trigger-width)] min-w-40 max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-white/10 bg-[#1b1e29] p-1.5 text-sm text-slate-200 shadow-2xl shadow-black/50">
          <Select.ScrollUpButton className="flex justify-center py-1"><ChevronUp className="h-4 w-4" /></Select.ScrollUpButton>
          <Select.Viewport>
            {options.map(option => (
              <Select.Item key={option.value} value={encode(option.value)} disabled={option.disabled} textValue={option.label} className="relative flex min-h-11 cursor-default select-none items-center rounded-lg py-2 pl-3 pr-9 outline-none data-[highlighted]:bg-violet-400/15 data-[highlighted]:text-violet-100 data-[state=checked]:text-violet-200 data-[disabled]:pointer-events-none data-[disabled]:opacity-40">
                <Select.ItemText><span className="break-words">{option.label}</span></Select.ItemText>
                <Select.ItemIndicator className="absolute right-3"><Check aria-hidden="true" className="h-4 w-4" /></Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
          <Select.ScrollDownButton className="flex justify-center py-1"><ChevronDown className="h-4 w-4" /></Select.ScrollDownButton>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  )
}
