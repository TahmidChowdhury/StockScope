'use client'

import { Component, createRef, type ComponentPropsWithoutRef } from 'react'

type Props = ComponentPropsWithoutRef<'section'> & { pending: boolean }
type Anchor = { element: Element; top: number; scroller: Element; key?: string }

// Measure when a request starts or settles. Native anchoring can lose its
// reference when a retry clears an error or results replace loading rows.
export default class ResearchPanel extends Component<Props> {
  private panel = createRef<HTMLElement>()

  getSnapshotBeforeUpdate(previous: Props): Anchor | null {
    const panel = this.panel.current
    if (previous.pending === this.props.pending || !panel) return null
    const main = panel.closest('main')
    if (!main) return null
    const mobile = window.matchMedia('(max-width: 1023px)').matches
    const scroller = mobile ? main : document.scrollingElement
    const top = mobile ? main.getBoundingClientRect().top : document.querySelector('.shell-topbar')?.getBoundingClientRect().bottom ?? 0
    if (!scroller || panel.getBoundingClientRect().top >= top) return null
    const bounds = main.getBoundingClientRect()
    const reader = document.elementFromPoint(bounds.left + bounds.width / 2, top + 8)
    if (!reader || !main.contains(reader) || reader.contains(panel)) return null
    if (!panel.contains(reader)) return { element: reader, top: reader.getBoundingClientRect().top, scroller }

    // Match chart and metric groups across the skeleton and the loaded layout.
    const groups = Array.from(panel.querySelectorAll<HTMLElement>('[data-reading-anchor]'))
    const group = groups.reverse().find(item => item.getBoundingClientRect().top <= top + 8)
    return group
      ? { element: group, top: group.getBoundingClientRect().top, scroller, key: group.dataset.readingAnchor }
      : { element: reader, top: reader.getBoundingClientRect().top, scroller }
  }

  componentDidUpdate(_previous: Props, _state: unknown, anchor: Anchor | null) {
    if (!anchor) return
    const element = anchor.key
      ? this.panel.current?.querySelector(`[data-reading-anchor="${anchor.key}"]`)
      : anchor.element
    if (element?.isConnected) {
      // A browser that already held this anchor in place needs no adjustment.
      const shift = element.getBoundingClientRect().top - anchor.top
      if (Math.abs(shift) > 1) anchor.scroller.scrollTop += shift
    }
  }

  render() {
    const { pending, ...props } = this.props
    return <section ref={this.panel} aria-busy={pending} {...props} />
  }
}
