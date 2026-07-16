import { brandAssets, brandColors } from '../../brand/tokens'
import { useEffect, type ReactNode } from 'react'
import { landingSeo } from '../../content/landing'

type Props = {
  children: ReactNode
}

function upsertMeta(attr: 'name' | 'property', key: string, content: string) {
  const selector = `meta[${attr}="${key}"]`
  let el = document.head.querySelector(selector) as HTMLMetaElement | null
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.content = content
}

function upsertLink(rel: string, href: string) {
  let el = document.head.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null
  if (!el) {
    el = document.createElement('link')
    el.rel = rel
    document.head.appendChild(el)
  }
  el.href = href
}

/**
 * Shell da landing: SEO + scroll próprio.
 * O app usa overflow:hidden em html/body/#root (Layout interno);
 * aqui o scroll vive neste container.
 */
export function MarketingLayout({ children }: Props) {
  useEffect(() => {
    const prevTitle = document.title
    document.title = landingSeo.title
    upsertMeta('name', 'description', landingSeo.description)
    upsertMeta('property', 'og:title', landingSeo.title)
    upsertMeta('property', 'og:description', landingSeo.description)
    upsertMeta('property', 'og:type', 'website')
    upsertMeta('property', 'og:locale', 'pt_BR')
    const ogImageUrl = new URL(landingSeo.ogImage, window.location.origin).href
    upsertMeta('property', 'og:image', ogImageUrl)
    upsertMeta('property', 'og:image:alt', landingSeo.ogImageAlt)
    upsertMeta('name', 'twitter:card', 'summary_large_image')
    upsertMeta('name', 'twitter:title', landingSeo.title)
    upsertMeta('name', 'twitter:description', landingSeo.description)
    upsertLink('canonical', window.location.origin + '/')

    return () => {
      document.title = prevTitle
    }
  }, [])

  return (
    <div
      className="relative h-dvh max-h-dvh overflow-x-hidden overflow-y-auto text-slate-100 antialiased"
      style={{
        fontFamily: '"Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif',
        backgroundColor: brandColors.deep,
      }}
      data-landing-scroll-root
    >
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
        style={{ backgroundColor: brandColors.deep }}
      >
        <img
          src={brandAssets.loginBackground}
          alt=""
          className="absolute inset-0 size-full object-cover object-center opacity-55"
          decoding="async"
          fetchPriority="high"
        />
        <div
          className="absolute inset-0"
          style={{
            background: `linear-gradient(165deg, ${brandColors.deep}ee 0%, ${brandColors.navy}cc 42%, ${brandColors.deep}f2 100%)`,
          }}
        />
      </div>
      {children}
    </div>
  )
}
