import Section from "@/components/Section";
import ServiceCard from "@/components/ServiceCard";
import { SERVICES } from "@/lib/services";

export default function ServicesPage() {
  return (
    <div className="min-h-screen py-12">
      <Section>
        <h1 className="text-4xl font-bold text-alloy-midnight mb-4">
          Our Services
        </h1>
        <p className="text-lg text-alloy-midnight/80 mb-12">
          Trusted home services in Bend, Oregon. Home cleaning is available now. More services coming soon.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {SERVICES.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>
      </Section>
    </div>
  );
}

