import type { ReactNode } from "react";

import { OwnerAlphaAccessPanel } from "./owner-alpha-access-panel";

export default function ReviewLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <>
      <div className="review-access-shell">
        <OwnerAlphaAccessPanel />
      </div>
      {children}
    </>
  );
}
