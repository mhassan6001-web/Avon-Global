"use client";

import { useEffect, useState } from "react";

import { Button, FormError, PageHeader, Panel, SelectField, TextField } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";
import { useStepUp } from "@/lib/auth/StepUpProvider";

import styles from "@/app/pages.module.css";

interface Profile {
  trading_name: string;
  legal_name: string | null;
  registration_status: "not_confirmed" | "pending" | "registered";
  registration_number: string | null;
  headquarters_city: string | null;
  headquarters_country_code: string | null;
  functional_currency: string;
  configured?: boolean;
}

export default function OrganisationPage() {
  const withStepUp = useStepUp();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void send<Profile>("GET", "/organisation/profile").then(({ data }) => setProfile(data));
  }, []);

  if (!profile) return null;
  const set = (patch: Partial<Profile>) => setProfile({ ...profile, ...patch });

  async function save() {
    if (!profile) return;
    setError(null);
    setSaved(false);
    const body: Partial<Profile> = { ...profile };
    delete body.configured;
    try {
      const { data } = await withStepUp(() =>
        send<Profile>("PUT", "/organisation/profile", {
          body: {
            ...body,
            legal_name: body.legal_name || null,
            registration_number: body.registration_number || null,
            headquarters_city: body.headquarters_city || null,
            headquarters_country_code: body.headquarters_country_code || null,
          },
        }),
      );
      setProfile(data);
      setSaved(true);
    } catch (e) {
      if (e instanceof ApiError && e.code === "cancelled") return;
      setError(e instanceof ApiError ? e.message : "Could not save.");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Organisation"
        description="Company identity is configuration. Registration is never assumed: it stays 'not confirmed' until you record it."
      />
      <Panel title="Organisation profile">
        <form
          className={styles.formGrid}
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <TextField
            label="Trading name"
            value={profile.trading_name}
            required
            onChange={(e) => set({ trading_name: e.target.value })}
          />
          <TextField
            label="Legal name"
            value={profile.legal_name ?? ""}
            onChange={(e) => set({ legal_name: e.target.value })}
          />
          <SelectField
            label="Registration status"
            value={profile.registration_status}
            onChange={(e) =>
              set({ registration_status: e.target.value as Profile["registration_status"] })
            }
            options={[
              { value: "not_confirmed", label: "Not confirmed" },
              { value: "pending", label: "Pending" },
              { value: "registered", label: "Registered" },
            ]}
          />
          <TextField
            label="Registration number"
            value={profile.registration_number ?? ""}
            hint="Required when status is Registered."
            onChange={(e) => set({ registration_number: e.target.value })}
          />
          <TextField
            label="Headquarters city"
            value={profile.headquarters_city ?? ""}
            onChange={(e) => set({ headquarters_city: e.target.value })}
          />
          <TextField
            label="Country code (e.g. MW)"
            value={profile.headquarters_country_code ?? ""}
            maxLength={2}
            onChange={(e) => set({ headquarters_country_code: e.target.value.toUpperCase() })}
          />
          <SelectField
            label="Functional currency"
            value={profile.functional_currency}
            onChange={(e) => set({ functional_currency: e.target.value })}
            options={["MWK", "USD", "ZAR", "ZMW"].map((c) => ({ value: c, label: c }))}
          />
          <div className={styles.field}>
            <Button variant="primary" type="submit">
              Save profile
            </Button>
          </div>
        </form>
        <FormError message={error} />
        {saved && (
          <p className={styles.notice} role="status">
            Saved and recorded in the audit log.
          </p>
        )}
      </Panel>
    </>
  );
}
