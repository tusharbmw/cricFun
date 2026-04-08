/**
 * Portfolio page — /tushar
 * Publicly accessible, no login required.
 * All content is static — no API calls.
 */

const ACCENT = '#2563eb'

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

const NAV_LINKS = [
  { href: '#about',        label: 'About' },
  { href: '#experience',   label: 'Experience' },
  { href: '#projects',     label: 'Projects' },
  { href: '#publications', label: 'Publications' },
  { href: '#skills',       label: 'Skills' },
  { href: '#contact',      label: 'Contact' },
]

const EXPERIENCE = [
  {
    company: 'Amazon Web Services (AWS)',
    role: 'Sr. Product Manager Technical (External Services)',
    period: 'Aug 2022 – Present',
    location: 'New York, NY',
    bullets: [
      'Launched AWS BCM Dashboards end-to-end: 150K+ MAU in 6 months, 75%+ CSAT, ~200K hours/month saved across customers.',
      'Led company-wide IAM access-control migration across millions of AWS accounts; 90%+ completion rate.',
      'Own AWS Cost Explorer — the 2nd most-used AWS service — with 1M+ weekly active users.',
    ],
  },
  {
    company: 'TS Imagine',
    role: 'Technical Operations Project Manager',
    period: 'Mar 2014 – Aug 2022',
    location: 'New York, NY · London, UK',
    bullets: [
      'Led technical operations for real-time portfolio risk and regulatory SaaS across Americas and EMEA.',
      'Built CI/CD pipelines that eliminated ~4 hours of manual work per release cycle.',
    ],
  },
  {
    company: 'Goldman Sachs (via Infosys)',
    role: 'Software Engineer / Tech Lead, Middle Office Technology',
    period: 'Jun 2006 – Mar 2014',
    location: 'New York · Tokyo · Hong Kong · Bengaluru',
    bullets: [
      'Built and maintained mission-critical equities and derivatives systems with 99%+ SLA compliance.',
      'Led incident management that reduced system downtime by 40%.',
    ],
  },
]

const PROJECTS = [
  {
    name: 'AWS BCM Dashboards',
    type: 'Product Launch',
    description:
      'Led end-to-end launch of AWS\'s new cost analytics dashboard product — from PRFAQ and pricing through GTM and post-launch iteration.',
    metrics: '150K+ MAU · 75%+ CSAT · ~200K hrs/month saved',
    links: [
      {
        label: 'Read the AWS Blog Post',
        url: 'https://aws.amazon.com/blogs/aws-cloud-financial-management/streamline-aws-cost-analytics-with-new-customized-billing-and-cost-management-dashboards/',
      },
    ],
  },
  {
    name: 'CapitalLens',
    type: 'Personal Project',
    description:
      'Self-hosted, free-to-run US stock portfolio tracker. Calculates XIRR, CAGR, and P&L benchmarked against the S&P 500.',
    stack: 'Python · Django · Oracle DB · OCI VPS · GitHub Actions',
    links: [
      { label: 'Live', url: 'https://capitallens.duckdns.org' },
      { label: 'GitHub', url: 'https://github.com/tusharbmw/capitallens' },
    ],
  },
  {
    name: 'cricFun',
    type: 'Personal Project',
    description:
      'Cricket prediction game for friends — pick match winners, apply powerups, and compete on a leaderboard. Running since 2020.',
    stack: 'Django 5.2 · React 19 · Vite · Tailwind CSS v4 · Oracle DB · Redis · Celery · GitHub Actions',
    links: [
      { label: 'Live', url: 'https://tushcricfun.us.to' },
      { label: 'GitHub', url: 'https://github.com/tusharbmw/cricFun' },
    ],
  },
]

const PUBLICATIONS = [
  {
    source: 'AWS Blog',
    title: 'Streamline AWS cost analytics with new customized Billing and Cost Management Dashboards',
    date: 'Aug 2025',
    url: 'https://aws.amazon.com/blogs/aws-cloud-financial-management/streamline-aws-cost-analytics-with-new-customized-billing-and-cost-management-dashboards/',
  },
  {
    source: 'AWS Docs',
    title: 'Billing & Cost Management Dashboards User Guide',
    date: null,
    url: 'https://docs.aws.amazon.com/cost-management/latest/userguide/dashboards.html',
  },
  {
    source: "AWS What's New",
    title: 'Dashboards launch',
    date: 'Aug 2025',
    url: 'https://aws.amazon.com/about-aws/whats-new/2025/08/aws-billing-cost-management-customizable-dashboards/',
  },
  {
    source: "AWS What's New",
    title: 'PDF/CSV exports for Dashboards',
    date: 'Dec 2025',
    url: 'https://aws.amazon.com/about-aws/whats-new/2025/12/aws-billing-cost-management-pdf-export-csv-data-download-dashboards/',
  },
  {
    source: 'AWS Announcements',
    title: 'Savings Plans launch in China',
    date: 'Jun 2023',
    url: 'https://www.amazonaws.cn/en/new/2023/announcing-savings-plans-in-amazon-web-services-china-regions/',
  },
  {
    source: 'AWS Docs',
    title: 'IAM Access Control Migration guide',
    date: 'Jun 2024',
    url: 'https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/migrate-granularaccess-whatis.html',
  },
]

const SKILLS = [
  {
    group: 'Product & Strategy',
    tags: [
      'Product strategy', 'Roadmapping', 'PRFAQ', 'Customer research',
      'Pricing & service limits', 'GTM', 'FinOps', 'API design',
      'Data quality', 'Multi-cloud',
    ],
  },
  {
    group: 'Program & Leadership',
    tags: [
      'Cross-functional leadership', 'Multi-org coordination', 'Stakeholder alignment',
      'Executive communication', 'OKRs', 'Risk management', 'Escalation management',
      'Regional expansion', 'GenAI for operations',
    ],
  },
  {
    group: 'Technical',
    tags: [
      'Python', 'SQL', 'Django', 'React',
      'AWS Cost Explorer', 'BCM Dashboards', 'CUR', 'QuickSight',
      'CI/CD', 'GitHub Actions', 'Redis', 'Celery', 'Oracle DB',
      'Distributed systems', 'Data pipelines',
    ],
  },
]

const FUN_FACTS = [
  {
    emoji: '🌏',
    stat: '5 countries lived · 28 visited',
    detail: 'India, Hong Kong, Japan, the UK, and the US. Always planning the next trip.',
  },
  {
    emoji: '🎓',
    stat: 'Manipal Institute of Technology',
    detail: 'Alumni include Satya Nadella (CEO, Microsoft) and Rajeev Suri (former CEO, Nokia).',
  },
  {
    emoji: '⛳',
    stat: 'Avid Golfer',
    detail: 'Always working on the handicap. Follows the game closely.',
  },
  {
    emoji: '📺',
    stat: 'Golf · F1 · Tennis · Cricket',
    detail: 'Also deep into tech trends and personal finance.',
  },
]

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeading({ children }) {
  return (
    <h2 className="text-xl font-bold text-gray-800 mb-6 pb-2 border-b border-gray-100">
      {children}
    </h2>
  )
}

function Tag({ children, accent }) {
  return (
    <span
      className="text-xs px-2.5 py-1 rounded-full font-medium"
      style={
        accent
          ? { background: '#EFF6FF', color: '#1d4ed8' }
          : { background: '#f3f4f6', color: '#374151' }
      }
    >
      {children}
    </span>
  )
}

function ExternalLink({ href, children, className = '' }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
    >
      {children}
    </a>
  )
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

function Hero() {
  return (
    <section id="hero" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
        {/* Photo / initials avatar */}
        <div className="shrink-0">
          <div className="w-24 h-24 md:w-28 md:h-28 rounded-full overflow-hidden border-2 border-gray-100 shadow-sm flex items-center justify-center"
            style={{ background: '#EFF6FF' }}>
            <img
              src="/tushar.jpg"
              alt="Tushar Mukherjee"
              className="w-full h-full object-cover"
              onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'flex' }}
            />
            <span className="text-3xl font-bold hidden items-center justify-center w-full h-full" style={{ color: ACCENT }}>
              TM
            </span>
          </div>
        </div>

        {/* Text */}
        <div className="flex-1 text-center md:text-left">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Tushar Mukherjee</h1>
          <p className="mt-1 text-sm md:text-base text-gray-500 font-medium">
            Sr. Technical Product Manager · AWS · FinOps · Financial Systems · Technical Program Management
          </p>
          <p className="mt-3 text-sm text-gray-600 leading-relaxed max-w-2xl">
            19 years building and shipping large-scale financial and cloud infrastructure products —
            from trading systems at Goldman Sachs to cost analytics tools used by 1M+ AWS customers every week.
          </p>

          <div className="mt-5 flex flex-wrap gap-3 justify-center md:justify-start">
            <ExternalLink
              href="/resume.pdf"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white transition hover:opacity-90"
              style={{ background: ACCENT }}
            >
              View Resume ↗
            </ExternalLink>
            <a
              href="mailto:tusharbmw@gmail.com"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition"
            >
              Get in Touch
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function About() {
  return (
    <section id="about" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>About Me</SectionHeading>
      <div className="space-y-4 text-sm text-gray-600 leading-relaxed">
        <p>
          I'm a Senior Technical Product Manager based in Jersey City, NJ, with 19 years spanning
          software engineering, technical program management, and product management across AWS, TS Imagine,
          and Goldman Sachs.
        </p>
        <p>
          At AWS, I own two of the most widely used cost and billing products:{' '}
          <strong className="text-gray-800">AWS Cost Explorer</strong> (the second most-used AWS service,
          with over 1 million weekly active users) and{' '}
          <strong className="text-gray-800">AWS Billing & Cost Management Dashboards</strong>, which I
          launched end-to-end and grew to 150,000+ monthly active users within six months.
        </p>
        <p>
          Before moving into product and program roles, I was a software engineer and tech lead building
          mission-critical trading and portfolio risk systems — which gives me genuine technical depth
          when working with engineering teams.
        </p>
        <p>
          My career has taken me across five countries — India, Hong Kong, Japan, the UK, and the US —
          living and working in each one. And beyond work, I love to travel: 28 countries and counting.
          That kind of global exposure shapes how I think about products, teams, and users.
        </p>
        <p>
          I studied Information Technology at Manipal Institute of Technology, an institution that has
          produced some remarkable alumni — including Satya Nadella, CEO of Microsoft, and Rajeev Suri,
          former CEO of Nokia.
        </p>
        <p>
          Outside of work, I build things: a self-hosted portfolio tracker (CapitalLens) and a cricket
          prediction game (cricFun — which you're looking at right now). I'm an avid golfer working on
          getting better, and I follow tech trends and personal finance closely. When I'm not on the
          course, you'll find me watching golf, F1, tennis, or cricket.
        </p>
      </div>
    </section>
  )
}

function Experience() {
  return (
    <section id="experience" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>Experience</SectionHeading>
      <div className="space-y-8">
        {EXPERIENCE.map((job, i) => (
          <div key={i} className="relative pl-4 border-l-2 border-gray-100">
            <div className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-blue-500" />
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-1 mb-1">
              <div>
                <h3 className="font-semibold text-gray-900 text-base">{job.company}</h3>
                <p className="text-sm text-gray-600">{job.role}</p>
              </div>
              <div className="text-xs text-gray-400 text-right shrink-0">
                <div>{job.period}</div>
                <div>{job.location}</div>
              </div>
            </div>
            <ul className="mt-2 space-y-1.5">
              {job.bullets.map((b, j) => (
                <li key={j} className="text-sm text-gray-600 flex gap-2">
                  <span className="text-blue-400 mt-0.5 shrink-0">›</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}

function Projects() {
  return (
    <section id="projects" className="space-y-0">
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
        <SectionHeading>Things I've Built</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PROJECTS.map((p, i) => (
            <div key={i} className="border border-gray-100 rounded-xl p-4 flex flex-col gap-3 hover:shadow-sm transition">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
                  style={{ background: '#EFF6FF', color: '#1d4ed8' }}>
                  {p.type}
                </span>
                <h3 className="mt-2 font-semibold text-gray-900">{p.name}</h3>
                <p className="mt-1 text-xs text-gray-500 leading-relaxed">{p.description}</p>
              </div>
              {p.metrics && (
                <p className="text-xs font-medium text-blue-600">{p.metrics}</p>
              )}
              {p.stack && (
                <p className="text-xs text-gray-400">{p.stack}</p>
              )}
              <div className="flex flex-wrap gap-2 mt-auto">
                {p.links.map((link, j) => (
                  <ExternalLink
                    key={j}
                    href={link.url}
                    className="text-xs font-medium text-blue-600 hover:underline"
                  >
                    {link.label} ↗
                  </ExternalLink>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Publications() {
  return (
    <section id="publications" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>Publications & Docs</SectionHeading>
      <ul className="space-y-3">
        {PUBLICATIONS.map((pub, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="text-[10px] font-semibold shrink-0 mt-0.5 px-2 py-0.5 rounded-full"
              style={{ background: '#f3f4f6', color: '#6b7280' }}>
              {pub.source}
            </span>
            <div className="flex-1 min-w-0">
              <ExternalLink
                href={pub.url}
                className="text-sm text-blue-600 hover:underline leading-snug"
              >
                {pub.title}
              </ExternalLink>
              {pub.date && (
                <span className="ml-2 text-xs text-gray-400">{pub.date}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Skills() {
  return (
    <section id="skills" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>Skills & Tools</SectionHeading>
      <div className="space-y-5">
        {SKILLS.map((group, i) => (
          <div key={i}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {group.group}
            </h3>
            <div className="flex flex-wrap gap-2">
              {group.tags.map((tag, j) => (
                <Tag key={j} accent={i === 2}>{tag}</Tag>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function FunFacts() {
  return (
    <section id="funfacts" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>A Few Things About Me</SectionHeading>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FUN_FACTS.map((fact, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
            <span className="text-2xl shrink-0">{fact.emoji}</span>
            <div>
              <p className="text-sm font-semibold text-gray-800">{fact.stat}</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-snug">{fact.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function Contact() {
  return (
    <section id="contact" className="bg-white border border-gray-100 rounded-xl shadow-sm p-6 md:p-8">
      <SectionHeading>Get in Touch</SectionHeading>
      <p className="text-sm text-gray-600 leading-relaxed mb-5">
        I'm currently open to senior Technical Product Manager and Technical Program Manager roles.
        If you're working on something interesting in cloud infrastructure, financial platforms, or
        data products — I'd love to talk.
      </p>
      <div className="flex flex-wrap gap-4">
        <a
          href="mailto:tusharbmw@gmail.com"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-blue-600 transition"
        >
          <span>✉</span> tusharbmw@gmail.com
        </a>
        <ExternalLink
          href="https://linkedin.com/in/tusharmukherjee"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-blue-600 transition"
        >
          <span>in</span> LinkedIn ↗
        </ExternalLink>
        <ExternalLink
          href="https://github.com/tusharbmw"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-blue-600 transition"
        >
          <span>⌥</span> GitHub ↗
        </ExternalLink>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Sticky nav
// ---------------------------------------------------------------------------

function StickyNav() {
  return (
    <nav className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-gray-100 shadow-sm">
      <div className="max-w-4xl mx-auto px-4">
        <div className="flex items-center justify-between h-12">
          <span className="font-semibold text-gray-800 text-sm">Tushar Mukherjee</span>
          <div className="hidden sm:flex items-center gap-4 overflow-x-auto">
            {NAV_LINKS.map(link => (
              <a
                key={link.href}
                href={link.href}
                className="text-xs font-medium text-gray-500 hover:text-blue-600 transition shrink-0"
              >
                {link.label}
              </a>
            ))}
          </div>
          {/* Mobile: scroll hint */}
          <div className="sm:hidden flex gap-3 overflow-x-auto max-w-[60vw] no-scrollbar">
            {NAV_LINKS.map(link => (
              <a
                key={link.href}
                href={link.href}
                className="text-xs font-medium text-gray-500 hover:text-blue-600 transition shrink-0"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Portfolio() {
  return (
    <div className="min-h-screen bg-[#f8f9fa]">
      <StickyNav />
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <Hero />
        <About />
        <Experience />
        <Projects />
        <Publications />
        <Skills />
        <FunFacts />
        <Contact />
      </main>
      <footer className="text-center text-xs text-gray-400 py-6">
        © Tushar Mukherjee · Built with React + Django
      </footer>
    </div>
  )
}
