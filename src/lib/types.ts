export type Product = {
  id: string;
  code: string;
  name: string;
  presentation: string;
  supplier: string;
  category: string;
  wholesalePrice: number | null;
  active: boolean;
  requiresReview: boolean;
  sourcePage?: number;
};

export type AppRole = "admin" | "employee" | "client";

export type Customer = {
  id: string;
  name: string;
  phone: string;
  address: string;
  document: string;
  notes: string;
  active: boolean;
};

export type ReceiptItem = {
  productId: string;
  code: string;
  name: string;
  presentation: string;
  quantity: number;
  unitPrice: number;
};

export type Receipt = {
  id: string;
  code: string;
  customerId?: string;
  customerName: string;
  customerPhone: string;
  customerAddress: string;
  issuedAt: string;
  items: ReceiptItem[];
  subtotal: number;
  discountPercentage: number;
  total: number;
  paymentMethod: "cash" | "transfer" | "account" | "mixed";
  paymentStatus: "paid" | "partial" | "pending";
  amountPaid: number;
  pendingAmount: number;
  status: "active" | "cancelled";
  notes: string;
};

export type Promotion = {
  name: string;
  minimumKg: number;
  discountPercentage: number;
};

export type AppData = {
  products: Product[];
  customers: Customer[];
  receipts: Receipt[];
};
