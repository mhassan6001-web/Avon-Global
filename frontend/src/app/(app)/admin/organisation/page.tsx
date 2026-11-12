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
  address_line1: string | null;
  address_line2: string | null;
  phone: string | null;
  email: string | null;
  tpin: string | null;
  vat_number: string | null;
  print_address: boolean;
  print_phone: boolean;
  print_email: boolean;
  print_tpin: boolean;
  print_vat: boolean;
  configured?: boolean;
}

const CONTACT_FIELDS = [
  { key: "address_line1", label: "Address line 1", flag: "print_address" },
  { key: "address_line2", label: "Address line 2", flag: null },
  { key: "phone", label: "Business telephone", flag: "print_phone" },
  { key: "email", label: "Business email", flag: "print_email" },
  { key: "tpin", label: "TPIN", flag: "print_tpin" },
  { key: "vat_number", label: "VAT registration number", flag: "print_vat" },
] as const;

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
            ...Object.fromEntries(CONTACT_FIELDS.map((f) => [f.key, body[f.key] || null])),
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
          {CONTACT_FIELDS.map((f) => (
            <div key={f.key} className={styles.field}>
              <TextField
                label={f.label}
                value={profile[f.key] ?? ""}
                onChange={(e) => set({ [f.key]: e.target.value } as Partial<Profile>)}
              />
              {f.flag && (
                <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6 }}>
                  <input
                    type="checkbox"
                    checked={profile[f.flag]}
                    disabled={!profile[f.key]}
                    onChange={(e) => set({ [f.flag]: e.target.checked } as Partial<Profile>)}
                  />
                  Approved to print on documents
                </label>
              )}
            </div>
          ))}
          <div className={styles.field}>
            <Button variant="primary" type="submit">
              Save profile
            </Button>
          </div>
        </form>
        <p className={styles.note}>
          Address, telephone, email, TPIN and VAT number appear on letterheads, quotations and
          invoices only after you tick “Approved to print”. Leave tax numbers unticked until the
          Malawi Revenue Authority has confirmed them.
        </p>
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
