import Section from "@/components/Section";
import GhlEmbed from "@/components/GhlEmbed";

export default function MoveOutPage() {
  return (
    <div className="min-h-screen">
      <Section className="py-12 md:py-20">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-alloy-midnight mb-4">
            Move-out / deep clean estimate
          </h1>
          <p className="text-lg text-alloy-midnight/80 mb-8">
            Tell us about your space and timeline. We'll provide a transparent estimate.
          </p>
          <div className="bg-white rounded-xl p-4 md:p-6 border border-alloy-stone/50">
            <GhlEmbed
              src="https://api.leadconnectorhq.com/widget/form/L8JC9XCbA0miUG3D7zIT"
              title="Move-Out / Heavy Clean Estimate"
              height={792}
            />
          </div>
        </div>
      </Section>
    </div>
  );
}

