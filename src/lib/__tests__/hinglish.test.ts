import { describe, expect, it } from "vitest";

import { codeMixRatio, toDevanagariApprox, toEnglishGloss } from "../hinglish";

describe("toEnglishGloss", () => {
  it("replaces known hinglish tokens", () => {
    expect(toEnglishGloss("yaar mera phone charge nahi ho raha hai")).toContain("my");
    expect(toEnglishGloss("yaar mera phone charge nahi ho raha hai")).toContain("is");
  });

  it("drops filler na", () => {
    expect(toEnglishGloss("bhejo na")).toBe("send");
    expect(toEnglishGloss("jaldi batao na")).toBe("quickly tell");
  });

  it("preserves punctuation and casing", () => {
    expect(toEnglishGloss("Mera phone slow hai, kya karun?")).toBe("My phone slow is, what do?");
  });

  it("is deterministic and keeps unknown tokens", () => {
    const t = "hostel ka wifi slow hai";
    expect(toEnglishGloss(t)).toContain("hostel");
    expect(toEnglishGloss(t)).toContain("wifi");
    expect(toEnglishGloss(t)).toBe(toEnglishGloss(t));
  });

  it("keeps numbers and mixed tokens", () => {
    expect(toEnglishGloss("15*8+22 ka answer kya hoga?")).toContain("15*8+22");
  });

  it("returns original for pure English", () => {
    const pure = "This is pure English text";
    expect(toEnglishGloss(pure)).toBe(pure);
  });

  it("handles empty", () => {
    expect(toEnglishGloss("")).toBe("");
  });
});

describe("toDevanagariApprox", () => {
  it("transliterates known words", () => {
    expect(toDevanagariApprox("yaar mera hostel")).toContain("यार");
    expect(toDevanagariApprox("mera")).toBe("मेरा");
  });

  it("uses long-ee for common possessives", () => {
    expect(toDevanagariApprox("meri")).toBe("मेरी");
    expect(toDevanagariApprox("teri")).toBe("तेरी");
    expect(toDevanagariApprox("yaar shivam meri jaan hai")).toContain("मेरी");
  });

  it("keeps unknown english", () => {
    expect(toDevanagariApprox("hello world")).toBe("hello world");
    expect(toDevanagariApprox("hello, meri world!")).toBe("hello, मेरी world!");
  });

  it("preserves punctuation", () => {
    expect(toDevanagariApprox("yaar, jaldi")).toContain("यार,");
  });
});

describe("codeMixRatio", () => {
  it("returns 0 for pure english", () => {
    expect(codeMixRatio("This is pure English text with no Hinglish")).toBe(0);
  });

  it("returns >0 for Hinglish", () => {
    expect(codeMixRatio("yaar mera phone charge nahi ho raha hai")).toBeGreaterThan(0.3);
  });

  it("counts Devanagari", () => {
    expect(codeMixRatio("यार मेरा फोन")).toBeGreaterThan(0.5);
  });

  it("returns 0 for empty", () => {
    expect(codeMixRatio("")).toBe(0);
  });

  it("is bounded 0..1", () => {
    for (const t of ["", "yaar", "hello world", "यार मेरा phone hai", "a b c d e f g"]) {
      const v = codeMixRatio(t);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
  });
});
