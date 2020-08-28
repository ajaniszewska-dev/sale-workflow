from odoo.exceptions import UserError

from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon


class TestProgramForFirstSaleOrder(TestSaleCouponCommon):
    def setUp(self):
        super(TestProgramForFirstSaleOrder, self).setUp()

        self.env["sale.coupon.program"].search([]).write({"active": False})

        self.product_A = self.env["product.product"].create(
            {"name": "Product A", "list_price": 60, "sale_ok": True}
        )

        self.program1 = self.env["sale.coupon.program"].create(
            {
                "name": "Get 10% discount for 1st order",
                "program_type": "promotion_program",
                "reward_type": "discount",
                "discount_type": "percentage",
                "discount_percentage": 10.0,
                "rule_min_quantity": 1,
                "rule_minimum_amount": 100.00,
                "promo_applicability": "on_current_order",
                "promo_code_usage": "no_code_needed",
                "maximum_use_number": 0,
                "first_order_only": True,
                "active": True,
            }
        )

        self.program2 = self.env["sale.coupon.program"].create(
            {
                "name": "Get 50% discount",
                "program_type": "promotion_program",
                "reward_type": "discount",
                "discount_type": "percentage",
                "discount_percentage": 50.0,
                "rule_min_quantity": 1,
                "rule_minimum_amount": 100.00,
                "promo_applicability": "on_current_order",
                "promo_code_usage": "no_code_needed",
                "maximum_use_number": 0,
                "active": False,
            }
        )

        self.program3 = self.env["sale.coupon.program"].create(
            {
                "name": "Get 30% discount with code",
                "program_type": "promotion_program",
                "reward_type": "discount",
                "discount_type": "percentage",
                "discount_percentage": 30.0,
                "rule_min_quantity": 1,
                "rule_minimum_amount": 100.00,
                "promo_applicability": "on_current_order",
                "promo_code_usage": "code_needed",
                "promo_code": "30_discount",
                "maximum_use_number": 0,
                "first_order_only": True,
                "active": True,
            }
        )

        self.partner1 = self.env["res.partner"].create({"name": "Jane Doe"})
        self.partner2 = self.env["res.partner"].create({"name": "John Doe"})
        self.partner3 = self.env["res.partner"].create({"name": "John Deere"})

    def create_sale_order(self, partner, qty):
        order = self.env["sale.order"].create({"partner_id": partner.id})
        order.write(
            {
                "order_line": [
                    (
                        0,
                        False,
                        {
                            "product_id": self.product_A.id,
                            "name": "Product A",
                            "product_uom_qty": qty,
                            "product_uom": self.uom_unit.id,
                        },
                    ),
                ]
            }
        )

        return order

    def process_coupon(self, order, code):
        self.env["sale.coupon.apply.code"].with_context(active_id=order.id).create(
            {"coupon_code": code}
        ).process_coupon()

    def test_promo_applied_on_first_so(self):

        order1 = self.create_sale_order(self.partner1, 2.0)
        order1.recompute_coupon_lines()

        discounts = set(order1.order_line.mapped("name")) - {"Product A"}

        self.assertEqual(len(discounts), 1, "Order should contain one discount")
        self.assertTrue(
            "Get 10% discount for 1st order" in discounts.pop(),
            "The discount should be a 10% discount",
        )
        self.assertEqual(
            len(order1.order_line.ids), 2, "The order should contain 2 lines"
        )

    def test_promo_first_and_second_so(self):

        order1 = self.create_sale_order(self.partner1, 2.0)
        order1.recompute_coupon_lines()
        discounts = set(order1.order_line.mapped("name")) - {"Product A"}

        self.assertEqual(
            len(order1.order_line.ids), 2, "The order should contain 2 lines"
        )
        self.assertEqual(len(discounts), 1, "Order should contain one discount")
        self.assertTrue(
            "Get 10% discount for 1st order" in discounts.pop(),
            "The discount should be a 10% discount",
        )

        self.program2.write({"active": True})

        order2 = self.create_sale_order(self.partner1, 4.0)
        order2.recompute_coupon_lines()
        discounts = set(order2.order_line.mapped("name")) - {"Product A"}

        self.assertEqual(
            len(order2.order_line.ids), 2, "The order should contain 2 lines"
        )
        self.assertEqual(len(discounts), 1, "Order should contain one discount")
        self.assertTrue(
            "Get 50% discount" in discounts.pop(),
            "The discount should be a 50% discount",
        )

    def test_promo_code_sale_order_program(self):

        self.env["sale.coupon.generate"].with_context(
            active_id=self.program3.id
        ).create({"generation_type": "nbr_coupon", "nbr_coupons": 1}).generate_coupon()

        order1 = self.create_sale_order(self.partner3, 2.0)
        self.process_coupon(order1, "30_discount")

        discounts = set(order1.order_line.mapped("name")) - {"Product A"}

        self.assertEqual(
            len(order1.order_line.ids), 2, "The order should contain 2 lines"
        )
        self.assertEqual(
            len(discounts),
            1,
            "the order should contain 1 Product A line and a discount",
        )
        self.assertTrue(
            "Get 30% discount with code" in discounts.pop(),
            "The discount should be a 50% discount",
        )

    def test_reused_code_promo_sale_order_program(self):

        order1 = self.create_sale_order(self.partner3, 5.0)
        self.process_coupon(order1, "30_discount")

        order2 = self.create_sale_order(self.partner3, 5.0)
        with self.assertRaises(UserError):
            self.process_coupon(order1, "30_discount")

        discounts = set(order2.order_line.mapped("name")) - {"Product A"}

        self.assertEqual(
            len(order2.order_line.ids), 1, "The order should contain 1 line"
        )
        self.assertEqual(
            len(discounts),
            0,
            "the order should contain 1 Product A line and no discounts",
        )
