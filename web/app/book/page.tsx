import Section from "@/components/Section";
import GhlEmbed from "@/components/GhlEmbed";

export default function BookPage() {
  return (
    <div className="min-h-screen">
      <Section className="py-12 md:py-20">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-alloy-midnight mb-4">
            Book your cleaning
          </h1>
          <p className="text-lg text-alloy-midnight/80 mb-8">
            Choose a time that works for you. We'll confirm by text.
          </p>
          <div className="bg-white rounded-xl p-4 md:p-6 border border-alloy-stone/50">
            <GhlEmbed
              src="https://api.leadconnectorhq.com/widget/booking/GficiTFm4cbAbQ05IHwz"
              title="Booking Calendar"
              height={1000}
            />
          </div>
          <p className="text-sm text-alloy-midnight/60 mt-6 text-center">
            Need to adjust your booking? Just reply to the text.
          </p>
        </div>
      </Section>
    </div>
  );
}

