/**
 * API integration layer for communicating with the Alloy backend dispatcher.
 */

const getApiBaseUrl = (): string => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL environment variable is not set");
  }
  return baseUrl;
};

export interface CleaningLeadPayload {
  name: string;
  email: string;
  phone: string;
  address?: string;
  city?: string;
  zip?: string;
  home_size?: string;
  bedrooms?: number;
  bathrooms?: number;
  preferred_frequency?: string;
  notes?: string;
}

export interface ProsApplicationPayload {
  name: string;
  phone: string;
  email: string;
  experience?: string;
  notes?: string;
}

export interface ApiResponse<T = any> {
  ok: boolean;
  message?: string;
  contact_id?: string;
  [key: string]: any;
}

/**
 * Submit a cleaning lead from the frontend.
 */
export async function submitCleaningLead(
  payload: CleaningLeadPayload
): Promise<ApiResponse> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/leads/cleaning`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to submit lead: ${res.statusText}`
    );
  }

  return res.json();
}

/**
 * Submit a pros application from the frontend.
 */
export async function submitProsApplication(
  payload: ProsApplicationPayload
): Promise<ApiResponse> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/leads/pros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to submit application: ${res.statusText}`
    );
  }

  return res.json();
}

