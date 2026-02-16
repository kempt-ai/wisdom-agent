'use client';

import { useMemo } from 'react';

interface InvestigationOverviewProps {
  overviewHtml: string;
  className?: string;
}

/**
 * Renders investigation overview HTML with colored links.
 *
 * Link format in the HTML:
 *   <a href="#def:slug" class="ab-link ab-definition">term</a>  -> blue
 *   <a href="#claim:slug" class="ab-link ab-claim">text</a>     -> orange
 *
 * This component processes the raw HTML and applies Tailwind-compatible
 * inline styles for the color coding.
 */
export function InvestigationOverview({ overviewHtml, className }: InvestigationOverviewProps) {
  const styledHtml = useMemo(() => {
    if (!overviewHtml) return '';

    // Replace ab-definition links with blue styling
    let html = overviewHtml.replace(
      /class="ab-link ab-definition"/g,
      'class="ab-link ab-definition" style="color: #2563eb; text-decoration: underline; text-decoration-color: #93bbfd; text-underline-offset: 2px; cursor: pointer;"'
    );

    // Replace ab-claim links with orange styling
    html = html.replace(
      /class="ab-link ab-claim"/g,
      'class="ab-link ab-claim" style="color: #ea580c; text-decoration: underline; text-decoration-color: #fdba74; text-underline-offset: 2px; cursor: pointer;"'
    );

    return html;
  }, [overviewHtml]);

  if (!overviewHtml) {
    return (
      <div className="text-slate-400 italic py-4">
        No overview content yet.
      </div>
    );
  }

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: styledHtml }}
      style={{ lineHeight: '1.8', fontSize: '1.1rem' }}
    />
  );
}
