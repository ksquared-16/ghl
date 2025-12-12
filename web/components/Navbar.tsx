"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import PrimaryButton from "./PrimaryButton";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const navLinks = [
    { href: "/services", label: "Services" },
    { href: "/pros", label: "For Pros" },
    { href: "/about", label: "About" },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-alloy-stone shadow-sm border-b border-alloy-stone/60">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Desktop Layout - Logo Left, Links Right */}
        <div className="hidden md:flex items-center justify-between h-20">
          {/* Logo - Left */}
          <Link href="/" className="flex items-center">
            <Image
              src="/brand/alloy-wordmark-blue.svg"
              alt="Alloy logo"
              width={180}
              height={48}
              className="h-12 w-auto"
              priority
            />
          </Link>

          {/* Navigation Links - Right Aligned */}
          <div className="flex items-center space-x-8">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || pathname?.startsWith(link.href + "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`
                    text-alloy-midnight hover:text-alloy-juniper 
                    transition-colors font-medium pb-1 relative
                    ${isActive ? "border-b-2 border-alloy-juniper" : ""}
                  `}
                >
                  {link.label}
                </Link>
              );
            })}
            <Link href="/services/cleaning">
              <PrimaryButton className="!px-5 !py-2 text-sm">
                Get a Quote
              </PrimaryButton>
            </Link>
          </div>
        </div>

        {/* Mobile Layout */}
        <div className="md:hidden flex items-center justify-between h-20 py-4">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <Image
              src="/brand/alloy-wordmark-blue.svg"
              alt="Alloy logo"
              width={140}
              height={36}
              className="h-9 w-auto"
              priority
            />
          </Link>

          {/* Mobile Menu Button */}
          <button
            className="p-3 rounded-md text-alloy-midnight hover:bg-white/50 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {mobileMenuOpen ? (
                <path d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-6 border-t border-alloy-midnight/10">
            <div className="flex flex-col space-y-5">
              {navLinks.map((link) => {
                const isActive = pathname === link.href || pathname?.startsWith(link.href + "/");
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`
                      text-alloy-midnight hover:text-alloy-juniper 
                      transition-colors font-medium py-2 relative
                      ${isActive ? "border-b-2 border-alloy-juniper inline-block w-fit" : ""}
                    `}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {link.label}
                  </Link>
                );
              })}
              <Link href="/services/cleaning" onClick={() => setMobileMenuOpen(false)}>
                <PrimaryButton className="w-full mt-2">Get a Quote</PrimaryButton>
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

