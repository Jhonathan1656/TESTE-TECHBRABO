import { Compass, LayoutDashboard } from "lucide-react";

import { ButtonLink } from "../../shared/components/Button";
import { Card } from "../../shared/components/Card";
import { PageHeader } from "../../shared/components/PageHeader";
import { EmptyState } from "../../shared/components/States";
import { t } from "../../shared/i18n/translate";

export function NotFoundPage() {
  return (
    <>
      <PageHeader title={t("errors.notFoundTitle")} />
      <Card>
        <EmptyState
          icon={<Compass size={20} />}
          action={
            <ButtonLink to="/" variant="primary" icon={<LayoutDashboard size={16} />}>
              {t("errors.goHome")}
            </ButtonLink>
          }
        >
          {t("errors.notFound")}
        </EmptyState>
      </Card>
    </>
  );
}
