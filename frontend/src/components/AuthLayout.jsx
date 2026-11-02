import React from "react";

export default function AuthLayout({ icon: Icon, title, subtitle, footer, children, nadicomBranding = false }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          {nadicomBranding ? (
            <div className="flex flex-col items-center gap-1 mb-5" aria-label="NADICOM">
              <img src="/nadicom-symbol.webp" alt="NADICOM symbol" className="h-28 w-28 object-contain" />
              <img src="/nadicom-wordmark.webp" alt="NADICOM" className="w-52 h-auto object-contain" />
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">BAWASLU Smart Radar</p>
            </div>
          ) : (
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary mb-4">
              <Icon className="w-7 h-7 text-primary-foreground" aria-hidden="true" />
            </div>
          )}
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-2">{subtitle}</p>}
        </div>
        <div className="bg-card rounded-2xl shadow-sm border border-border p-8">
          {children}
        </div>
        {footer && (
          <p className="text-center text-sm text-muted-foreground mt-6">{footer}</p>
        )}
      </div>
    </div>
  );
}
