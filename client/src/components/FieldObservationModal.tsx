import { useState } from "react";
import { Camera, Crosshair, LoaderCircle, ShieldCheck, X } from "lucide-react";
import { trpc } from "@/lib/trpc";

type Props = { open: boolean; onClose: () => void };
type FormState = { observedAt: string; latitude: string; longitude: string; locationAccuracyM: string; impactClass: "flooded" | "water_on_road" | "access_disrupted" | "no_flood_observed"; waterDepthCm: string; notes: string; photo: { dataUrl: string; contentType: "image/jpeg" | "image/png" | "image/webp"; filename: string } | null };

function freshForm(): FormState {
  return { observedAt: new Date().toISOString().slice(0, 16), latitude: "", longitude: "", locationAccuracyM: "", impactClass: "flooded", waterDepthCm: "", notes: "", photo: null };
}

export function FieldObservationModal({ open, onClose }: Props) {
  const utils = trpc.useUtils();
  const [form, setForm] = useState<FormState>(freshForm);
  const [message, setMessage] = useState<string | null>(null);
  const summary = trpc.observations.summary.useQuery();
  const mine = trpc.observations.mine.useQuery();
  const submit = trpc.observations.submit.useMutation({
    onSuccess: async () => {
      setForm(freshForm());
      setMessage("Observation submitted for analyst review. It does not create an alert.");
      await Promise.all([utils.observations.summary.invalidate(), utils.observations.mine.invalidate()]);
    },
    onError: error => setMessage(error.message),
  });

  if (!open) return null;
  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm(current => ({ ...current, [key]: value }));
  const useLocation = () => {
    if (!navigator.geolocation) { setMessage("Location capture is not available in this browser."); return; }
    navigator.geolocation.getCurrentPosition(position => {
      update("latitude", position.coords.latitude.toFixed(6));
      update("longitude", position.coords.longitude.toFixed(6));
      update("locationAccuracyM", position.coords.accuracy.toFixed(1));
      setMessage("Location captured. Please confirm it before submitting.");
    }, () => setMessage("Location permission was unavailable. Enter coordinates manually."), { enableHighAccuracy: true, timeout: 12_000 });
  };
  const choosePhoto = (file?: File) => {
    if (!file) return;
    if (!( ["image/jpeg", "image/png", "image/webp"] as const).includes(file.type as "image/jpeg" | "image/png" | "image/webp")) { setMessage("Use JPG, PNG, or WebP only."); return; }
    if (file.size > 900_000) { setMessage("Photo must be 900 KB or smaller for secure upload."); return; }
    const reader = new FileReader();
    reader.onload = () => update("photo", { dataUrl: String(reader.result), contentType: file.type as "image/jpeg" | "image/png" | "image/webp", filename: file.name });
    reader.readAsDataURL(file);
  };
  const submitObservation = () => {
    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) { setMessage("Valid latitude and longitude are required."); return; }
    submit.mutate({ observedAt: new Date(form.observedAt), latitude, longitude, locationAccuracyM: form.locationAccuracyM ? Number(form.locationAccuracyM) : null, impactClass: form.impactClass, waterDepthCm: form.waterDepthCm ? Number(form.waterDepthCm) : null, notes: form.notes || null, photo: form.photo });
  };

  return <div className="modal-backdrop observation-backdrop" role="presentation"><section className="observation-modal" role="dialog" aria-modal="true" aria-labelledby="observation-title"><button className="close-button" type="button" onClick={onClose} aria-label="Close field observation"><X size={18} /></button><span className="eyebrow">Prospective validation evidence</span><h1 id="observation-title">Submit field observation</h1><p className="observation-lede">No sign-in is required. This browser receives a private anonymous contributor identifier to enforce submission limits and show only its own recent entries. Submitted evidence always requires analyst review and never creates a public flood alert or model label automatically.</p><div className="evidence-summary"><ShieldCheck size={16} /><span>{summary.data?.verified ?? 0} verified · {summary.data?.submitted ?? 0} awaiting review</span><small>Matching readiness: {summary.data?.prospectiveMatchingReadiness?.status?.replaceAll("_", " ") ?? "loading"}. {summary.data?.prospectiveMatchingReadiness?.reason ?? "No matching metric or model promotion is authorized."}</small></div><div className="observation-form"><label>Observed time<input type="datetime-local" value={form.observedAt} onChange={event => update("observedAt", event.target.value)} /></label><div className="observation-grid"><label>Latitude<input inputMode="decimal" value={form.latitude} onChange={event => update("latitude", event.target.value)} placeholder="16.724700" /></label><label>Longitude<input inputMode="decimal" value={form.longitude} onChange={event => update("longitude", event.target.value)} placeholder="95.668700" /></label></div><button type="button" className="location-button" onClick={useLocation}><Crosshair size={15} />Use current location</button><div className="observation-grid"><label>Impact class<select value={form.impactClass} onChange={event => update("impactClass", event.target.value as FormState["impactClass"])}><option value="flooded">Flooded area</option><option value="water_on_road">Water on road</option><option value="access_disrupted">Access disrupted</option><option value="no_flood_observed">No flood observed</option></select></label><label>Water depth (cm)<input inputMode="decimal" value={form.waterDepthCm} onChange={event => update("waterDepthCm", event.target.value)} placeholder="Optional" /></label></div><label>Location accuracy (m)<input inputMode="decimal" value={form.locationAccuracyM} onChange={event => update("locationAccuracyM", event.target.value)} placeholder="Optional" /></label><label>Field note<textarea value={form.notes} onChange={event => update("notes", event.target.value)} maxLength={1200} placeholder="Road, village context, timing, or observed impacts (optional)" /></label><label>Photo evidence <small>Optional · JPG/PNG/WebP up to 900 KB</small><input type="file" accept="image/jpeg,image/png,image/webp" onChange={event => choosePhoto(event.target.files?.[0])} /></label>{form.photo && <small className="photo-ready"><Camera size={13} />{form.photo.filename} ready for secure upload</small>}</div><button type="button" className="primary-button submit-observation" onClick={submitObservation} disabled={submit.isPending}>{submit.isPending ? <><LoaderCircle size={15} />Submitting</> : "Submit for analyst review"}</button>{mine.data?.length ? <p className="my-observation-count">This browser's recent entries: {mine.data.length}. Review state is visible only in this browser and to authorized analysts.</p> : null}{message && <p className="form-message">{message}</p>}</section></div>;
}
