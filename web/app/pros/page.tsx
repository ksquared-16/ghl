import Section from "@/components/Section";
import GhlEmbed from "@/components/GhlEmbed";

export default function ProsPage() {
  const benefits = [
    "Pick your own jobs and set your schedule",
    "We handle the busywork—marketing, booking, customer communication",
    "Fair pay. You keep more of what you earn",
    "Get paid promptly after job completion",
    "Real humans behind Alloy, not a faceless platform",
  ];

  const expectations = [
    "Valid insurance and background check",
    "Professional, reliable service",
    "Responsive to job opportunities",
    "Commitment to quality work",
  ];

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <Section className="py-12 md:py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-alloy-midnight mb-4">
            Great cleaners deserve great customers.
          </h1>
          <p className="text-lg text-alloy-midnight/80 mb-8">
            We help you get quality jobs. We handle the busywork—marketing, booking, customer communication. You focus on the work.
          </p>
        </div>
      </Section>

      {/* How It Works */}
      <Section className="py-16 bg-white">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-8 text-center">
          How it works for cleaners
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {[
            {
              step: "1",
              title: "Apply",
              description:
                "Tell us about your experience. Simple application, no lengthy forms.",
            },
            {
              step: "2",
              title: "Get verified",
              description:
                "We verify your insurance, background, and credentials. Real humans review every application.",
            },
            {
              step: "3",
              title: "Accept jobs",
              description:
                "We text you when jobs match your schedule. You pick the ones that work for you.",
            },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-16 h-16 bg-alloy-blue text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                {item.step}
              </div>
              <h3 className="text-xl font-semibold text-alloy-midnight mb-2">
                {item.title}
              </h3>
              <p className="text-gray-600">{item.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Benefits */}
      <Section className="py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 max-w-4xl mx-auto">
          <div>
            <h2 className="text-2xl font-bold text-alloy-midnight mb-6">
              Benefits
            </h2>
            <ul className="space-y-4">
              {benefits.map((benefit, i) => (
                <li key={i} className="flex items-start">
                  <span className="text-alloy-juniper mr-3 text-xl">✓</span>
                  <span className="text-gray-700">{benefit}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-alloy-midnight mb-6">
              Expectations
            </h2>
            <ul className="space-y-4">
              {expectations.map((expectation, i) => (
                <li key={i} className="flex items-start">
                  <span className="text-alloy-blue mr-3 text-xl">•</span>
                  <span className="text-gray-700">{expectation}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* Application Form */}
      <Section className="py-16 bg-white">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold text-alloy-midnight mb-4 text-center">
            Apply to work with Alloy
          </h2>
          <p className="text-center text-alloy-midnight/80 mb-8">
            Fill out the form below. We'll review your application and be in touch soon.
          </p>
          <GhlEmbed
            src="https://api.leadconnectorhq.com/widget/form/S4ajOQFaanzumo8eyadC"
            title="Subcontractor Onboarding"
            height={1845}
          />
        </div>
      </Section>
    </div>
  );
}

