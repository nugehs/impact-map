import { refundBooking } from "../src/bookings/refunds";

test("creates a refund for a booking payment", async () => {
  const refund = await refundBooking("booking_123", "pi_123");
  expect(refund.status).toBe("pending");
});
