import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "./features/auth/LoginPage";
import { RequireAuth } from "./features/auth/RequireAuth";
import { AppLayout } from "./features/layout/AppLayout";

// Route-level code splitting: the login screen and the shell load first, each page on demand.
const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const BatchListPage = lazy(() => import("./features/batches/BatchListPage").then((m) => ({ default: m.BatchListPage })));
const BatchReviewPage = lazy(() =>
  import("./features/batches/BatchReviewPage").then((m) => ({ default: m.BatchReviewPage })),
);
const UploadPage = lazy(() => import("./features/upload/UploadPage").then((m) => ({ default: m.UploadPage })));
const QuotePage = lazy(() => import("./features/quote/QuotePage").then((m) => ({ default: m.QuotePage })));
const PlanListPage = lazy(() => import("./features/plans/PlanListPage").then((m) => ({ default: m.PlanListPage })));
const PlanDetailPage = lazy(() => import("./features/plans/PlanDetailPage").then((m) => ({ default: m.PlanDetailPage })));
const SourcesPage = lazy(() => import("./features/sources/SourcesPage").then((m) => ({ default: m.SourcesPage })));
const NotFoundPage = lazy(() => import("./features/layout/NotFoundPage").then((m) => ({ default: m.NotFoundPage })));

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="batches" element={<BatchListPage />} />
        <Route path="batches/:batchId" element={<BatchReviewPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="quote" element={<QuotePage />} />
        <Route path="plans" element={<PlanListPage />} />
        <Route path="plans/:planId" element={<PlanDetailPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="home" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
