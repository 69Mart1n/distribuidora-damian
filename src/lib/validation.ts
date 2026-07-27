import { z } from "zod";

const safeText = (maximum: number) =>
  z
    .string()
    .trim()
    .max(maximum)
    .refine((value) => !/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(value), {
      message: "El texto contiene caracteres no permitidos",
    });

export const newProductSchema = z.object({
  code: safeText(40).min(1),
  name: safeText(200).min(1),
  presentation: safeText(100).min(1),
  supplier: safeText(120).min(1),
  category: safeText(80).min(1),
  wholesalePrice: z.number().finite().min(0).max(99_999_999).nullable(),
});

export const newCustomerSchema = z.object({
  name: safeText(200).min(1),
  phone: safeText(40),
  address: safeText(300),
  document: safeText(80),
  notes: safeText(2000),
});

export const newReceiptSchema = z.object({
  customerId: z.string().max(100).optional(),
  customerName: safeText(200).min(1),
  customerPhone: safeText(40),
  customerAddress: safeText(300),
  items: z
    .array(
      z.object({
        productId: z.string().max(100),
        code: safeText(40),
        name: safeText(200).min(1),
        presentation: safeText(100),
        quantity: z.number().finite().positive().max(100_000),
        unitPrice: z.number().finite().min(0).max(99_999_999),
      }),
    )
    .min(1)
    .max(500),
  discountPercentage: z.number().finite().min(0).max(100),
  paymentMethod: z.enum(["cash", "transfer", "account", "mixed"]),
  amountPaid: z.number().finite().min(0).max(999_999_999),
  notes: safeText(2000),
});
