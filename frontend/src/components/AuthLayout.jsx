import React from "react";

/**
 * Public authentication shell. Login branding follows the operational workspace
 * palette without changing any authorization or form behavior.
 */
export default function AuthLayout({ icon: Icon, title, subtitle, footer, children, nadicomBranding = false }) {
  if (nadicomBranding) {
    return (
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#f1f5f7] px-4 py-10 sm:px-6">
        <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-2 bg-[#122f46]" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-20 -top-36 h-96 w-96 rounded-full border-[65px] border-[#dfe9ed]/70" />
        <div className="relative w-full max-w-[520px]">
          <div className="overflow-hidden rounded-[22px] border border-[#dce5eb] bg-white shadow-[0_24px_70px_-42px_rgba(18,47,70,0.5)]">
            <div className="border-b border-[#e3ebef] bg-[#f7fafb] px-5 py-5 sm:px-9">
              <div className="flex items-center justify-center gap-3 sm:gap-5" aria-label="BAWASLU and NADICOM">
                <div className="flex min-w-0 flex-[1.4] items-center justify-center">
                  <img src="/bawaslu-full-logo.webp" alt="BAWASLU — Badan Pengawas Pemilihan Umum" className="w-full max-w-[230px] object-contain" />
                </div>
                <div aria-hidden="true" className="h-14 w-px shrink-0 bg-[#c9d8df]" />
                <div className="flex min-w-0 flex-1 items-center justify-center">
                  <img src="/nadicom-wordmark.webp" alt="NADICOM" className="w-full max-w-[152px] object-contain" />
                </div>
              </div>
            </div>
            <div className="px-6 pb-8 pt-8 sm:px-10">
              <div className="mb-7 text-center">
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[#11816d]">BAWASLU Smart Radar</p>
                <h1 className="text-[27px] font-bold tracking-tight text-[#152c47] sm:text-3xl">{title}</h1>
                {subtitle && <p className="mt-2 text-sm text-[#60768c]">{subtitle}</p>}
              </div>
              {children}
            </div>
          </div>
          {footer && <p className="mt-6 text-center text-sm text-[#60768c]">{footer}</p>}
          <p className="mt-5 text-center text-[11px] font-medium tracking-wide text-[#71889a]">Secure BAWASLU intelligence workspace</p>
        </div>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary mb-4">
            <Icon className="w-7 h-7 text-primary-foreground" aria-hidden="true" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-2">{subtitle}</p>}
        </div>
        <div className="bg-card rounded-2xl shadow-sm border border-border p-8">{children}</div>
        {footer && <p className="text-center text-sm text-muted-foreground mt-6">{footer}</p>}
      </div>
    </div>
  );
}
