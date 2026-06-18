<template>
  <div class="page-stack">
    <section class="panel">
      <div class="panel-head">
        <h2>待缴账单</h2>
        <button @click="load">刷新</button>
      </div>
      <DataTable :columns="billColumns" :rows="unpaidBills">
        <template #cell-status="{ row }"><StatusBadge :status="row.status" /></template>
        <template #cell-amount="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template>
        <template #cell-prepaid_balance="{ row }">
          <span class="balance-amount">¥{{ Number(row.prepaid_balance).toFixed(2) }}</span>
        </template>
        <template #actions="{ row }">
          <button @click="openPayDialog(row)">缴费</button>
        </template>
      </DataTable>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>缴费记录</h2>
      </div>
      <DataTable :columns="paymentColumns" :rows="payments">
        <template #cell-amount="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template>
        <template #cell-prepaid_deduct="{ row }">
          <span v-if="Number(row.prepaid_deduct) > 0" class="txn-out">-¥{{ Number(row.prepaid_deduct).toFixed(2) }}</span>
          <span v-else>-</span>
        </template>
        <template #cell-actual_paid="{ row }">¥{{ Number(row.actual_paid).toFixed(2) }}</template>
      </DataTable>
    </section>

    <div v-if="payDialog.visible" class="modal-overlay" @click.self="closePayDialog">
      <div class="modal">
        <div class="modal-head">
          <h3>确认缴费</h3>
          <button class="close-btn" @click="closePayDialog">×</button>
        </div>
        <div class="modal-body">
          <div class="pay-summary">
            <div class="pay-row">
              <span>房屋</span>
              <strong>{{ payDialog.bill.room_label }}</strong>
            </div>
            <div class="pay-row">
              <span>业主</span>
              <strong>{{ payDialog.bill.owner_name }}</strong>
            </div>
            <div class="pay-row">
              <span>费用</span>
              <strong>{{ payDialog.bill.fee_name }} {{ payDialog.bill.period }}</strong>
            </div>
            <div class="pay-row">
              <span>账单编号</span>
              <strong>{{ payDialog.bill.bill_no }}</strong>
            </div>
            <hr />
            <div class="pay-row highlight">
              <span>应收金额</span>
              <strong>¥{{ Number(payDialog.bill.amount).toFixed(2) }}</strong>
            </div>
            <div class="pay-row">
              <span>预存款余额</span>
              <strong class="balance-amount">¥{{ Number(payDialog.bill.prepaid_balance).toFixed(2) }}</strong>
            </div>
            <div class="pay-row checkbox-row" v-if="Number(payDialog.bill.prepaid_balance) > 0">
              <label class="checkbox-label">
                <input type="checkbox" v-model="payDialog.use_prepaid" />
                <span>使用预存款抵扣</span>
              </label>
            </div>
            <div class="pay-row deduction-row" v-if="payDialog.use_prepaid && Number(payDialog.bill.prepaid_balance) > 0">
              <span>预存款抵扣</span>
              <strong class="txn-out">-¥{{ Number(estimatedDeduct).toFixed(2) }}</strong>
            </div>
            <hr />
            <div class="pay-row total-row">
              <span>还需支付</span>
              <strong class="final-amount">¥{{ Number(estimatedActualPaid).toFixed(2) }}</strong>
            </div>
            <div class="pay-row">
              <span>支付方式</span>
              <select v-model="payDialog.method">
                <option value="wechat">微信</option>
                <option value="alipay">支付宝</option>
                <option value="bank">银行卡</option>
                <option value="cash">现金</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="secondary-btn" @click="closePayDialog">取消</button>
          <button @click="confirmPay" :disabled="payDialog.loading">
            {{ payDialog.loading ? '处理中...' : '确认缴费' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="successDialog.visible" class="modal-overlay">
      <div class="modal success-modal">
        <div class="success-icon">✓</div>
        <h3 class="success-title">缴费成功</h3>
        <div class="success-details">
          <div class="pay-row">
            <span>应收金额</span>
            <strong>¥{{ Number(successDialog.result.amount).toFixed(2) }}</strong>
          </div>
          <div class="pay-row" v-if="Number(successDialog.result.prepaid_deduct) > 0">
            <span>预存款抵扣</span>
            <strong class="txn-out">-¥{{ Number(successDialog.result.prepaid_deduct).toFixed(2) }}</strong>
          </div>
          <div class="pay-row total-row">
            <span>实付金额</span>
            <strong class="final-amount">¥{{ Number(successDialog.result.actual_paid).toFixed(2) }}</strong>
          </div>
          <div class="pay-row">
            <span>支付方式</span>
            <strong>{{ successDialog.result.method }}</strong>
          </div>
          <div class="pay-row">
            <span>票据编号</span>
            <strong>{{ successDialog.result.receipt_no }}</strong>
          </div>
        </div>
        <button @click="closeSuccessDialog" class="full-width-btn">完成</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { propertyApi } from "../api/property";
import DataTable from "../components/DataTable.vue";
import StatusBadge from "../components/StatusBadge.vue";

const bills = ref([]);
const payments = ref([]);

const unpaidBills = computed(() => bills.value.filter((bill) => ["unpaid", "overdue"].includes(bill.status)));

const billColumns = [
  { key: "bill_no", label: "账单编号" },
  { key: "room_label", label: "房屋" },
  { key: "owner_name", label: "业主" },
  { key: "amount", label: "应收金额" },
  { key: "prepaid_balance", label: "预存款余额" },
  { key: "due_date", label: "截止日期" },
  { key: "status", label: "状态" }
];

const paymentColumns = [
  { key: "receipt_no", label: "票据编号" },
  { key: "bill_no", label: "账单编号" },
  { key: "room_label", label: "房屋" },
  { key: "owner_name", label: "付款人" },
  { key: "amount", label: "应收金额" },
  { key: "prepaid_deduct", label: "预存款抵扣" },
  { key: "actual_paid", label: "实付金额" },
  { key: "method", label: "方式" },
  { key: "paid_at", label: "支付时间" }
];

const payDialog = reactive({
  visible: false,
  bill: {},
  use_prepaid: true,
  method: "wechat",
  loading: false
});

const successDialog = reactive({
  visible: false,
  result: {}
});

const estimatedDeduct = computed(() => {
  if (!payDialog.use_prepaid || !payDialog.bill) return "0.00";
  const balance = Number(payDialog.bill.prepaid_balance || 0);
  const amount = Number(payDialog.bill.amount || 0);
  return Math.min(balance, amount).toFixed(2);
});

const estimatedActualPaid = computed(() => {
  const amount = Number(payDialog.bill.amount || 0);
  const deduct = Number(estimatedDeduct.value);
  return (amount - deduct).toFixed(2);
});

async function load() {
  [bills.value, payments.value] = await Promise.all([propertyApi.listBills(), propertyApi.listPayments()]);
}

function openPayDialog(row) {
  payDialog.bill = { ...row };
  payDialog.use_prepaid = Number(row.prepaid_balance) > 0;
  payDialog.method = "wechat";
  payDialog.loading = false;
  payDialog.visible = true;
}

function closePayDialog() {
  payDialog.visible = false;
}

async function confirmPay() {
  payDialog.loading = true;
  try {
    const result = await propertyApi.payBill(payDialog.bill.id, {
      method: payDialog.method,
      payer: payDialog.bill.owner_name,
      use_prepaid: payDialog.use_prepaid
    });
    payDialog.visible = false;
    successDialog.result = result;
    successDialog.visible = true;
    await load();
  } finally {
    payDialog.loading = false;
  }
}

function closeSuccessDialog() {
  successDialog.visible = false;
}

onMounted(load);
</script>
