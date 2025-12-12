import Link from "next/link";
import Section from "@/components/Section";
import PrimaryButton from "@/components/PrimaryButton";
import Accordion from "@/components/Accordion";
import GhlEmbed from "@/components/GhlEmbed";

export default function CleaningPage() {
  const cleaningOptions = [
    {
      type: "Standard",
      description:
        "Regular maintenance cleaning to keep your home fresh and tidy.",
    },
    {
      type: "Deep",
      description:
        "Thorough cleaning including baseboards, inside appliances, and detailed scrubbing.",
    },
    {
      type: "Move-out",
      description:
        "Comprehensive cleaning to prepare your home for the next residents.",
    },
  ];

  const frequencies = [
    { label: "One-time", description: "Perfect for special occasions or trying us out." },
    { label: "Weekly", description: "Keep your home consistently clean every week." },
    { label: "Bi-weekly", description: "Every other week for regular maintenance." },
    { label: "Monthly", description: "Monthly deep clean to keep things fresh." },
  ];

  const whatsIncluded = {
    kitchen: [
      "Clean and sanitize countertops",
      "Wipe down appliances",
      "Clean inside microwave",
      "Sweep and mop floors",
      "Take out trash",
    ],
    bathrooms: [
      "Clean and sanitize toilets",
      "Scrub showers and tubs",
      "Clean mirrors and fixtures",
      "Wipe down surfaces",
      "Sweep and mop floors",
    ],
    living: [
      "Dust all surfaces",
      "Vacuum carpets and rugs",
      "Mop hard floors",
      "Clean windowsills",
      "Organize and tidy",
    ],
    bedrooms: [
      "Make beds",
      "Dust furniture",
      "Vacuum floors",
      "Empty trash",
      "Tidy surfaces",
    ],
  };

  const cleaningFaqs = [
    {
      question: "What's included in a standard cleaning?",
      answer:
        "Standard cleaning covers the basics: dusting, vacuuming, mopping, bathroom and kitchen cleaning, making beds, and taking out trash. See the 'What's Included' section above for the full list.",
    },
    {
      question: "Do I need to be home during the cleaning?",
      answer:
        "No. We'll coordinate access with you beforehand. Most customers provide a key or code, or schedule the cleaning when they'll be away.",
    },
    {
      question: "What if I'm not satisfied with the cleaning?",
      answer:
        "We make it right. If something isn't up to your standards, let us know within 24 hours and we'll send the pro back to fix it at no charge.",
    },
    {
      question: "How much does cleaning cost?",
      answer:
        "Pricing depends on your home size, frequency, and specific needs. Request a quote and we'll give you a transparent estimate. No surprises.",
    },
    {
      question: "Are cleaning supplies included?",
      answer:
        "Yes. Pros bring all necessary supplies and equipment. You don't need to provide anything unless you have specific product preferences.",
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <Section className="py-12 md:py-20">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-alloy-midnight mb-4">
            Home cleaning in Bend, no guesswork.
          </h1>
          <p className="text-lg text-alloy-midnight/80 mb-8">
            We match you with vetted, insured cleaners in Bend. One-time, weekly, bi-weekly, or monthly—your choice. Clear expectations, fair pricing, real results.
          </p>
        </div>
      </Section>

      {/* Quote Form */}
      <Section id="quote-form" className="py-12 bg-white">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-alloy-midnight mb-6">
            Get a quote
          </h2>
          <GhlEmbed
            src="https://api.leadconnectorhq.com/widget/form/JBZiHlFyWKli2GnSwivI"
            title="Lead Form"
            height={1470}
          />
        </div>
      </Section>

      {/* Why Book Through Alloy */}
      <Section className="py-16">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-8 text-center">
          Why book through Alloy
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            {
              title: "Vetted, insured pros",
              description:
                "Every cleaner is background-checked and verified. We stand behind every match.",
            },
            {
              title: "Confirm by text",
              description:
                "No apps to download. We text you the details, you confirm. Simple.",
            },
            {
              title: "Fair pricing",
              description:
                "Transparent pricing, no hidden fees. Pros get fair pay, you get fair prices.",
            },
            {
              title: "Local to Bend",
              description:
                "Supporting neighborhood businesses and the people who run them.",
            },
            {
              title: "We make it right",
              description:
                "If something's not up to your standards, let us know within 24 hours and we'll fix it.",
            },
            {
              title: "Your schedule, your way",
              description:
                "Choose your frequency. Change it anytime. No contracts, no hassle.",
            },
          ].map((point) => (
            <div
              key={point.title}
              className="bg-white rounded-lg p-6 border border-gray-200"
            >
              <h3 className="text-xl font-semibold text-alloy-blue mb-2">
                {point.title}
              </h3>
              <p className="text-gray-600">{point.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Cleaning Options */}
      <Section className="py-16 bg-white">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-8 text-center">
          Cleaning Options
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {cleaningOptions.map((option) => {
            const isMoveOut = option.type === "Move-out";
            const content = (
              <div className="bg-alloy-stone rounded-lg p-6 border border-gray-200">
                <h3 className="text-xl font-semibold text-alloy-midnight mb-2">
                  {option.type} Cleaning
                </h3>
                <p className="text-gray-600">{option.description}</p>
              </div>
            );
            return isMoveOut ? (
              <Link key={option.type} href="/services/cleaning/move-out">
                {content}
              </Link>
            ) : (
              <div key={option.type}>{content}</div>
            );
          })}
        </div>

        <h3 className="text-2xl font-bold text-alloy-midnight mb-6 text-center">
          Cleaning Frequencies
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {frequencies.map((freq) => (
            <div
              key={freq.label}
              className="bg-white rounded-lg p-4 border border-gray-200 text-center"
            >
              <h4 className="font-semibold text-alloy-blue mb-2">
                {freq.label}
              </h4>
              <p className="text-sm text-gray-600">{freq.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* What's Included */}
      <Section className="py-16">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-8 text-center">
          What's Included (Standard Clean)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(whatsIncluded).map(([room, tasks]) => (
            <div key={room} className="bg-white rounded-lg p-6 border border-gray-200">
              <h3 className="text-lg font-semibold text-alloy-midnight mb-3 capitalize">
                {room === "living" ? "Living Areas" : room}
              </h3>
              <ul className="space-y-2">
                {tasks.map((task, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start">
                    <span className="text-alloy-juniper mr-2">•</span>
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {/* FAQ */}
      <Section className="py-16 bg-white">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-8 text-center">
          Frequently Asked Questions
        </h2>
        <div className="max-w-3xl mx-auto">
          {cleaningFaqs.map((faq) => (
            <Accordion key={faq.question} title={faq.question}>
              <p>{faq.answer}</p>
            </Accordion>
          ))}
        </div>
      </Section>

      {/* Secondary CTA */}
      <Section className="py-16">
        <div className="bg-alloy-pine rounded-lg p-8 md:p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
          <p className="text-lg mb-6 opacity-90">
            Submit your quote request above. We'll text you shortly to confirm details.
          </p>
          <a href="#quote-form">
            <PrimaryButton className="bg-white text-alloy-pine hover:bg-alloy-stone">
              Start my quote
            </PrimaryButton>
          </a>
        </div>
      </Section>
    </div>
  );
}

