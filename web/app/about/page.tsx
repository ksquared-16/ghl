import Section from "@/components/Section";

export default function AboutPage() {
  const values = [
    {
      title: "Trust First",
      description:
        "Every pro is vetted. Quality is guaranteed. Alloy stands behind every match. Trust is non-negotiable.",
    },
    {
      title: "Fair for Everyone",
      description:
        "Fair pricing for customers, better earnings for pros. No hidden fees, no surprises. Win-win is the only way.",
    },
    {
      title: "Human + Smart",
      description:
        "Real people + smart tech, always together. We use technology to make things easier, but real humans are always there when you need them.",
    },
    {
      title: "Dead-Simple",
      description:
        "Booking and getting work should feel instant and effortless. No complicated apps, no confusing processes. It just works.",
    },
    {
      title: "Local Proud",
      description:
        "We champion neighborhood businesses and local pros. Based in Bend, supporting Bend. Building stronger communities, one job at a time.",
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <Section className="py-12 md:py-20">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-alloy-midnight mb-4">
            About Alloy
          </h1>
          <p className="text-lg text-alloy-midnight/80 mb-8">
            Finding reliable home service professionals shouldn't be complicated. We match you with trusted local pros—vetted, insured, and ready to do great work. Starting with home cleaning in Bend, Oregon.
          </p>
          <p className="text-lg text-alloy-midnight/80">
            We make it effortless for customers to find pros they can trust, and for great pros to grow their businesses. Fast, reliable connections powered by smart technology and real human care.
          </p>
        </div>
      </Section>

      {/* Mission */}
      <Section className="py-16 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-alloy-midnight mb-6 text-center">
            Our Mission
          </h2>
          <p className="text-lg text-alloy-midnight/80 text-center">
            A world where every home or business project is matched with the perfect local pro in minutes—no stress, no guesswork, and no bad experiences. Creating stronger communities one perfect job at a time.
          </p>
        </div>
      </Section>

      {/* Values */}
      <Section className="py-16">
        <h2 className="text-3xl font-bold text-alloy-midnight mb-12 text-center">
          Our Values
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {values.map((value) => (
            <div
              key={value.title}
              className="bg-white rounded-lg p-6 border border-gray-200"
            >
              <h3 className="text-xl font-semibold text-alloy-blue mb-3">
                {value.title}
              </h3>
              <p className="text-gray-600">{value.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Local Focus */}
      <Section className="py-16 bg-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-alloy-midnight mb-6">
            Local Focus, Bend Roots
          </h2>
          <p className="text-lg text-alloy-midnight/80 mb-4">
            Alloy is based in Bend, Oregon. We're not a faceless corporation—we're your neighbors, building a service that works for our community.
          </p>
          <p className="text-lg text-alloy-midnight/80">
            When you book through Alloy, you're supporting local businesses and helping build a stronger, more connected Bend.
          </p>
        </div>
      </Section>
    </div>
  );
}

