import { describe, expect, it } from "vitest";

describe("Copernicus CDS API credential", () => {
  it("is accepted by the official profile verification API", async () => {
    const token = process.env.CDS_API_KEY;
    expect(token, "CDS_API_KEY must be configured for this test").toBeTruthy();

    const response = await fetch("https://cds.climate.copernicus.eu/api/profiles/v1/account/verification/pat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "PRIVATE-TOKEN": token,
      },
    });

    expect(response.status, "CDS rejected the configured credential").not.toBe(401);
    expect(response.status, "CDS rejected the configured credential").not.toBe(403);
  }, 30_000);
});
