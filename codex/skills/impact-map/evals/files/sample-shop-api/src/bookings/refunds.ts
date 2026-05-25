import { createStripeRefund } from "../payments/stripe";

export async function refundBooking(bookingId: string, paymentIntentId: string) {
  return createStripeRefund({
    bookingId,
    paymentIntentId,
    reason: "requested_by_customer"
  });
}
