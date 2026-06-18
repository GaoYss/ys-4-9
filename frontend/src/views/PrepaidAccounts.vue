<template>
  <div class="split-layout">
    <section class="panel form-panel">
      <h2>充值</h2>
      <form @submit.prevent="recharge" class="form-grid">
        <label>选择房屋
          <select v-model="rechargeForm.account_id" required>
            <option value="" disabled>请选择</option>
            <option v-for="account in accounts" :key="account.id" :value="account.id">
              {{ account.room_label }} - {{ account.owner_name }} (余额: ¥{{ Number(account.balance).toFixed(2) }})
            </option>
          </select>
        </label>
        <label>充值金额<input v-model.number="rechargeForm.amount" type="number" min="0.01" step="0.01" required /></label>
        <label>备注<input v-model="rechargeForm.remark" placeholder="可选" /></label>
        <button type="submit">确认充值</button>
      </form>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>预存款账户</h2>
        <button @click="load">刷新</button>
      </div>
      <DataTable :columns="accountColumns" :rows="accounts">
        <template #cell-balance="{ row }">¥{{ Number(row.balance).toFixed(2) }}</template>
      </DataTable>

      <div class="panel-head section-gap">
        <h2>流水记录</h2>
      </div>
      <DataTable :columns="txnColumns" :rows="transactions">
        <template #cell-amount="{ row }">
          <span :class="row.txn_type === 'recharge' ? 'txn-in' : 'txn-out'">
            {{ row.txn_type === 'recharge' ? '+' : '-' }}¥{{ Number(row.amount).toFixed(2) }}
          </span>
        </template>
        <template #cell-balance_after="{ row }">¥{{ Number(row.balance_after).toFixed(2) }}</template>
        <template #cell-txn_type="{ row }">
          <span class="status-badge" :class="row.txn_type === 'recharge' ? 'paid' : 'overdue'">
            {{ row.txn_type === 'recharge' ? '充值' : '抵扣' }}
          </span>
        </template>
      </DataTable>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { propertyApi } from "../api/property";
import DataTable from "../components/DataTable.vue";

const accounts = ref([]);
const transactions = ref([]);
const rechargeForm = reactive({ account_id: "", amount: 0, remark: "" });

const accountColumns = [
  { key: "room_label", label: "房屋" },
  { key: "owner_name", label: "业主" },
  { key: "balance", label: "余额" },
  { key: "updated_at", label: "更新时间" }
];

const txnColumns = [
  { key: "txn_no", label: "流水号" },
  { key: "room_label", label: "房屋" },
  { key: "owner_name", label: "业主" },
  { key: "txn_type", label: "类型" },
  { key: "amount", label: "金额" },
  { key: "balance_after", label: "余额" },
  { key: "bill_no", label: "关联账单" },
  { key: "remark", label: "备注" },
  { key: "created_at", label: "时间" }
];

async function load() {
  [accounts.value, transactions.value] = await Promise.all([
    propertyApi.listPrepaidAccounts(),
    propertyApi.listAllPrepaidTransactions()
  ]);
}

async function recharge() {
  await propertyApi.rechargePrepaid(rechargeForm.account_id, {
    amount: rechargeForm.amount,
    remark: rechargeForm.remark
  });
  Object.assign(rechargeForm, { account_id: "", amount: 0, remark: "" });
  await load();
}

onMounted(load);
</script>
