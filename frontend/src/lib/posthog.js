import posthog from 'posthog-js'

const key = import.meta.env.VITE_POSTHOG_KEY
if (key) {
  posthog.init(key, {
    api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: false,   // handled manually for SPA route changes
    capture_pageleave: true,
    person_profiles: 'identified_only',
  })
}

export default posthog
