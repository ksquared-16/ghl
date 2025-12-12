import Link from "next/link";
import Image from "next/image";
import Section from "@/components/Section";
import PrimaryButton from "@/components/PrimaryButton";
import SecondaryButton from "@/components/SecondaryButton";
import ServiceCard from "@/components/ServiceCard";
import Accordion from "@/components/Accordion";
import GhlEmbed from "@/components/GhlEmbed";
import BrandValueCard from "@/components/BrandValueCard";
import { SERVICES } from "@/lib/services";

export default function Home() {
  const howItWorksSteps = [
    {
      number: "1",
      title: "Tell us what you need",
      description: "Share your home size and schedule. No complicated forms.",
    },
    {
      number: "2",
      title: "We match you with someone you can trust",
      description: "Every pro is vetted, insured, and background-checked. We stand behind every match.",
    },
    {
      number: "3",
      title: "Confirm by text",
      description: "We text you the details. You confirm. That's it. No apps, no hassle.",
    },
  ];

  const brandValues = [
    {
      title: "Trust First",
      description:
        "We vet every pro, guarantee quality, and stand behind every match. Trust is non-negotiable.",
      accentColor: "juniper" as const,
    },
    {
      title: "Fair for Everyone",
      description:
        "Customers pay fair prices. Pros keep more of what they earn. Win-win is the only way.",
      accentColor: "ember" as const,
    },
    {
      title: "Human + Smart",
      description:
        "We combine real people who care with powerful technology - never one without the other.",
      accentColor: "blue" as const,
    },
    {
      title: "Dead-Simple",
      description:
        "Life's complicated enough. Booking help or getting jobs should feel instant and effortless.",
      accentColor: "juniper" as const,
    },
  ];

  const faqs = [
    {
      question: "How does Alloy work?",
      answer:
        "You tell us what you need, we match you with a vetted local pro, and you confirm by text. No apps, no complicated booking. We handle the rest.",
    },
    {
      question: "Are the professionals insured?",
      answer:
        "Yes. Every pro is insured, background-checked, and verified before they can accept jobs. We stand behind every match.",
    },
    {
      question: "What areas do you serve?",
      answer:
        "We're focused on Bend, Oregon right now. We'll expand to surrounding areas as we grow.",
    },
    {
      question: "How do I pay?",
      answer:
        "We securely save your payment method and only charge it after the work is done — no deposits, no surprises.",
    },
    {
      question: "Can I schedule recurring cleanings?",
      answer:
        "Set up weekly, bi-weekly, or monthly cleanings. More frequent service may qualify for preferred pricing — just let us know your schedule when you request a quote.",
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-alloy-stone">
        <div className="mx-auto max-w-6xl px-4 md:px-8 py-10 md:py-8">
          <div className="relative h-[340px] md:h-[400px] lg:h-[460px] overflow-hidden rounded-xl shadow-lg">
            {/* Background Image */}
            <Image
              src="/hero/cleaning-hero.jpg"
              alt="Clean modern home interior"
              fill
              priority
              className="object-cover"
              sizes="(max-width: 768px) 100vw, (max-width: 1024px) 90vw, 1152px"
            />

            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-alloy-midnight/60 via-alloy-midnight/25 to-transparent" />

            {/* Content Overlay */}
            <div className="relative z-10 flex h-full items-center px-6 md:px-10 lg:px-12">
              <div className="max-w-xl space-y-4 md:space-y-6">
                <p className="text-sm font-medium text-alloy-juniper uppercase tracking-wide">
                  Born in Bend. Built for trust.
                </p>
                <h1 className="text-4xl md:text-5xl lg:text-5xl font-bold text-white leading-tight">
                  Find trusted local pros,{" "}
                  <span className="relative inline-block">
                    <span className="text-white">no guesswork</span>
                    <span className="absolute bottom-0 left-0 right-0 h-1 bg-alloy-juniper/60 -z-10"></span>
                  </span>
                  .
                </h1>
                <p className="text-lg text-white/90">
                  We match you with vetted, insured professionals in Bend. Starting with home cleaning. Real people, real results.
                </p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Link href="/services/cleaning">
                    <PrimaryButton className="w-full sm:w-auto">
                      Get a cleaning quote
                    </PrimaryButton>
                  </Link>
                  <Link href="#how-it-works">
                    <SecondaryButton className="!bg-white/20 backdrop-blur-md !border !border-white/50 !text-white hover:!bg-white/30 w-full sm:w-auto">
                      See how Alloy works
                    </SecondaryButton>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How Alloy Works */}
      <Section id="how-it-works" className="py-10 bg-alloy-stone">
        <h2 className="text-3xl font-bold text-alloy-pine text-center mb-12">
          How Alloy Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {howItWorksSteps.map((step) => (
            <div key={step.number} className="text-center">
              <div className="w-16 h-16 bg-alloy-juniper text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4 shadow-md">
                {step.number}
              </div>
              <h3 className="text-xl font-semibold text-alloy-pine mb-2">
                {step.title}
              </h3>
              <p className="text-alloy-midnight/80">{step.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Current Services */}
      <Section className="py-20">
        <h2 className="text-3xl font-bold text-alloy-pine text-center mb-4">
          Services we offer
        </h2>
        <p className="text-center text-alloy-midnight/80 mb-12">
          Home cleaning is available now. More services coming soon.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SERVICES.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>
      </Section>

      {/* Brand Values */}
      <Section className="py-20 bg-white">
        <h2 className="text-3xl font-bold text-alloy-pine text-center mb-4">
          Why Alloy Exists
        </h2>
        <p className="text-center text-alloy-midnight/80 mb-12 max-w-2xl mx-auto">
          These principles guide how we vet pros, set prices, and build technology. No shortcuts.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {brandValues.map((value) => (
            <BrandValueCard
              key={value.title}
              title={value.title}
              description={value.description}
              accentColor={value.accentColor}
              icon={
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              }
            />
          ))}
        </div>
      </Section>

      {/* Testimonials */}
      <Section className="py-20 bg-alloy-pine/5">
        <h2 className="text-3xl font-bold text-alloy-pine text-center mb-12">
          What our customers say
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-white rounded-2xl shadow-md p-6 border border-alloy-stone/50"
            >
              <p className="text-alloy-midnight/80 mb-4">
                "Finally, a cleaner I can trust. The whole process was simple, and the work was exactly what I needed."
              </p>
              <p className="font-semibold text-alloy-pine">
                — Sarah M., Bend
              </p>
            </div>
          ))}
        </div>
      </Section>

      {/* FAQ */}
      <Section className="py-20 bg-white">
        <h2 className="text-3xl font-bold text-alloy-midnight text-center mb-12">
          Frequently Asked Questions
        </h2>
        <div className="max-w-3xl mx-auto">
          {faqs.map((faq) => (
            <Accordion key={faq.question} title={faq.question}>
              <p>{faq.answer}</p>
            </Accordion>
          ))}
        </div>
      </Section>

      {/* Final CTA */}
      <Section className="py-16">
        <div className="bg-alloy-blue rounded-lg p-8 md:p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
          <p className="text-lg mb-6 opacity-90">
            Get a quote. We'll text you to confirm details. No pressure, no hassle.
          </p>
          <div className="max-w-2xl mx-auto">
            <GhlEmbed
              src="https://api.leadconnectorhq.com/widget/form/JBZiHlFyWKli2GnSwivI"
              title="Lead Form"
              height={1470}
            />
          </div>
        </div>
      </Section>
    </div>
  );
}
