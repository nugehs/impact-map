type RefundRequest = {
  bookingId: string;
  paymentIntentId: string;
  reason: string;
};

export async function createStripeRefund(request: RefundRequest) {
  return {
    id: `refund_${request.bookingId}`,
    paymentIntentId: request.paymentIntentId,
    status: "pending"
  };
}
