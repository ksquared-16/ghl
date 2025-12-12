import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  const footerLinks = {
    services: [
      { href: "/services", label: "Services" },
      { href: "/services/cleaning", label: "Home Cleaning" },
    ],
    company: [
      { href: "/about", label: "About" },
      { href: "/pros", label: "For Pros" },
    ],
    legal: [
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
    ],
  };

  return (
    <footer className="bg-alloy-midnight text-alloy-stone mt-20 relative">
      {/* Subtle gradient border at top */}
      <div className="h-1 bg-gradient-to-r from-alloy-pine via-alloy-juniper to-alloy-pine"></div>
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <Image
                src="/brand/alloy-brandmark-blue.svg"
                alt="Alloy brandmark"
                width={40}
                height={40}
                className="h-10 w-10"
              />
              <p className="text-sm text-white/90">
                Alloy LLC – Bend, Oregon
              </p>
            </div>
            <p className="text-alloy-stone mb-4">
              Connecting homeowners with trusted local service professionals.
            </p>
          </div>

          {/* Services */}
          <div>
            <h4 className="font-semibold mb-4 text-white/90">Services</h4>
            <ul className="space-y-2">
              {footerLinks.services.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-alloy-stone hover:text-alloy-juniper transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company & Legal */}
          <div>
            <h4 className="font-semibold mb-4 text-white/90">Company</h4>
            <ul className="space-y-2 mb-6">
              {footerLinks.company.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-alloy-stone hover:text-alloy-juniper transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
            <h4 className="font-semibold mb-4 text-white/90">Legal</h4>
            <ul className="space-y-2">
              {footerLinks.legal.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-alloy-stone hover:text-alloy-juniper transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-white/10 mt-8 pt-8 text-center text-sm text-alloy-stone/80">
          <p>&copy; {new Date().getFullYear()} Alloy LLC. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}

