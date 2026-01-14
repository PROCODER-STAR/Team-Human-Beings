import React, { useState, useEffect } from 'react';
import { Camera, Upload, TrendingUp, AlertCircle, DollarSign, Calendar, PieChart, BarChart3, Download, RefreshCw } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, PieChart as RechartsPie, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

const ReceiptExpenseTracker = () => {
  const [receipts, setReceipts] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [budgetLimit, setBudgetLimit] = useState(1000);
  const [activeTab, setActiveTab] = useState('upload');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const stored = await window.storage.get('receipts-data');
        if (stored) {
          setReceipts(JSON.parse(stored.value));
        } else {
          generateDemoData();
        }
      } catch (e) {
        generateDemoData();
      }
    };
    loadData();
  }, []);

  const saveData = async (data) => {
    try {
      await window.storage.set('receipts-data', JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save:', e);
    }
  };

  const generateDemoData = () => {
    const stores = ['Walmart', 'Target', 'Starbucks', 'Shell Gas', 'CVS Pharmacy', 'Amazon Fresh', 'McDonalds', 'Whole Foods', 'Best Buy', 'Home Depot'];
    const demoReceipts = [];
    const startDate = new Date('2024-01-01');
    
    for (let i = 0; i < 50; i++) {
      const daysOffset = Math.floor(Math.random() * 365);
      const receiptDate = new Date(startDate);
      receiptDate.setDate(receiptDate.getDate() + daysOffset);
      
      const store = stores[Math.floor(Math.random() * stores.length)];
      const categoryMap = {
        'Walmart': 'Food', 'Target': 'Shopping', 'Starbucks': 'Dining',
        'Shell Gas': 'Transport', 'CVS Pharmacy': 'Healthcare', 'Amazon Fresh': 'Food',
        'McDonalds': 'Dining', 'Whole Foods': 'Food', 'Best Buy': 'Shopping',
        'Home Depot': 'Shopping'
      };
      
      const numItems = Math.floor(Math.random() * 8) + 2;
      const items = [];
      let total = 0;
      
      for (let j = 0; j < numItems; j++) {
        const price = parseFloat((Math.random() * 40 + 5).toFixed(2));
        total += price;
        items.push({ name: 'Item ' + (j + 1), price: price });
      }
      
      demoReceipts.push({
        id: Date.now() + i,
        receipt_id: 'RCP_' + String(i + 1).padStart(4, '0'),
        date: receiptDate.toISOString().slice(0, 10),
        store: store,
        category: categoryMap[store] || 'Other',
        items: items,
        total: parseFloat(total.toFixed(2)),
        processed: new Date().toISOString()
      });
    }
    
    setReceipts(demoReceipts);
    saveData(demoReceipts);
  };

  const processReceipt = (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const stores = ['Walmart', 'Target', 'Starbucks', 'Shell Gas', 'CVS Pharmacy', 'Amazon Fresh'];
        const categories = ['Food', 'Transport', 'Shopping', 'Healthcare', 'Dining'];
        
        const store = stores[Math.floor(Math.random() * stores.length)];
        const numItems = Math.floor(Math.random() * 8) + 2;
        const items = [];
        let total = 0;
        
        for (let j = 0; j < numItems; j++) {
          const price = parseFloat((Math.random() * 40 + 5).toFixed(2));
          total += price;
          items.push({ name: 'Item ' + (j + 1), price });
        }
        
        const receipt = {
          id: Date.now() + Math.random(),
          receipt_id: 'RCP_' + String(receipts.length + 1).padStart(4, '0'),
          date: new Date().toISOString().slice(0, 10),
          store: store,
          total: parseFloat(total.toFixed(2)),
          category: categories[Math.floor(Math.random() * categories.length)],
          items: items,
          image: e.target.result,
          processed: new Date().toISOString()
        };
        resolve(receipt);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleFileUpload = async (e) => {
    setProcessing(true);
    const files = Array.from(e.target.files);
    const processed = [];
    
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        const receipt = await processReceipt(file);
        processed.push(receipt);
      }
    }
    
    const updated = [...receipts, ...processed];
    setReceipts(updated);
    saveData(updated);
    setProcessing(false);
  };

  const getMonthlyData = () => {
    return receipts.filter(r => r.date.startsWith(selectedMonth));
  };

  const getAllMonthsData = () => {
    const monthlyData = {};
    receipts.forEach(r => {
      const month = r.date.slice(0, 7);
      monthlyData[month] = (monthlyData[month] || 0) + parseFloat(r.total);
    });
    return Object.entries(monthlyData)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, total]) => ({
        month: new Date(month + '-01').toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
        total: parseFloat(total.toFixed(2))
      }));
  };

  const getTotalSpending = () => {
    return getMonthlyData().reduce((sum, r) => sum + parseFloat(r.total), 0).toFixed(2);
  };

  const getCategoryBreakdown = () => {
    const data = {};
    getMonthlyData().forEach(r => {
      data[r.category] = (data[r.category] || 0) + parseFloat(r.total);
    });
    return Object.entries(data).map(([name, value]) => ({
      name,
      value: parseFloat(value.toFixed(2))
    })).sort((a, b) => b.value - a.value);
  };

  const getDailySpending = () => {
    const data = {};
    getMonthlyData().forEach(r => {
      data[r.date] = (data[r.date] || 0) + parseFloat(r.total);
    });
    return Object.entries(data)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, amount]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        amount: parseFloat(amount.toFixed(2))
      }));
  };

  const getTopStores = () => {
    const data = {};
    getMonthlyData().forEach(r => {
      data[r.store] = (data[r.store] || 0) + parseFloat(r.total);
    });
    return Object.entries(data)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([store, amount]) => ({
        store,
        amount: parseFloat(amount.toFixed(2))
      }));
  };

  const getAlerts = () => {
    const total = parseFloat(getTotalSpending());
    const alerts = [];
    
    if (total > budgetLimit) {
      alerts.push({
        type: 'danger',
        message: 'Budget exceeded by $' + (total - budgetLimit).toFixed(2) + '!'
      });
    } else if (total > budgetLimit * 0.8) {
      alerts.push({
        type: 'warning',
        message: 'Warning: ' + ((total / budgetLimit) * 100).toFixed(0) + '% of budget used'
      });
    } else {
      alerts.push({
        type: 'success',
        message: 'On track: ' + ((total / budgetLimit) * 100).toFixed(0) + '% of budget used'
      });
    }

    const categoryData = getCategoryBreakdown();
    if (categoryData.length > 0) {
      const topCategory = categoryData[0];
      if (topCategory.value > total * 0.4) {
        alerts.push({
          type: 'info',
          message: topCategory.name + ' is your top category at ' + ((topCategory.value / total) * 100).toFixed(0) + '%'
        });
      }
    }

    return alerts;
  };

  const exportToCSV = () => {
    const headers = ['Receipt ID', 'Date', 'Store', 'Category', 'Total', 'Items Count'];
    const rows = receipts.map(r => [
      r.receipt_id,
      r.date,
      r.store,
      r.category,
      r.total,
      r.items.length
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'receipts_export_' + selectedMonth + '.csv';
    a.click();
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-3xl shadow-2xl overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-8 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold flex items-center gap-3 mb-2">
                  <Camera className="w-10 h-10" />
                  Receipt Analytics Dashboard
                </h1>
                <p className="text-blue-100 text-lg">SROIE Dataset Processing & Expense Insights</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold">${getTotalSpending()}</div>
                <div className="text-blue-100">Total This Month</div>
              </div>
            </div>
          </div>

          <div className="flex border-b bg-gray-50">
            {[
              { id: 'upload', label: 'Upload', icon: Upload },
              { id: 'summary', label: 'Summary', icon: DollarSign },
              { id: 'analytics', label: 'Analytics', icon: TrendingUp },
              { id: 'reports', label: 'Reports', icon: BarChart3 }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={'flex-1 py-4 px-6 font-semibold transition-all flex items-center justify-center gap-2 ' + (
                  activeTab === tab.id
                    ? 'bg-white text-blue-600 border-b-4 border-blue-600 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100'
                )}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-8">
            {activeTab === 'upload' && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-blue-100 font-medium">Total Receipts</p>
                      <Calendar className="w-8 h-8 opacity-80" />
                    </div>
                    <p className="text-4xl font-bold">{receipts.length}</p>
                    <p className="text-sm text-blue-100 mt-2">Processed from SROIE</p>
                  </div>
                  
                  <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white shadow-lg">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-green-100 font-medium">This Month</p>
                      <PieChart className="w-8 h-8 opacity-80" />
                    </div>
                    <p className="text-4xl font-bold">{getMonthlyData().length}</p>
                    <p className="text-sm text-green-100 mt-2">Receipts</p>
                  </div>
                  
                  <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-purple-100 font-medium">Categories</p>
                      <BarChart3 className="w-8 h-8 opacity-80" />
                    </div>
                    <p className="text-4xl font-bold">{new Set(receipts.map(r => r.category)).size}</p>
                    <p className="text-sm text-purple-100 mt-2">Tracked</p>
                  </div>
                </div>

                <div className="border-4 border-dashed border-blue-300 rounded-2xl p-16 text-center bg-gradient-to-br from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-all">
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="receipt-upload"
                    disabled={processing}
                  />
                  <label htmlFor="receipt-upload" className="cursor-pointer">
                    {processing ? (
                      <RefreshCw className="w-20 h-20 mx-auto text-blue-600 mb-4 animate-spin" />
                    ) : (
                      <Upload className="w-20 h-20 mx-auto text-blue-600 mb-4" />
                    )}
                    <p className="text-2xl font-bold text-gray-700 mb-3">
                      {processing ? 'Processing...' : 'Upload Receipt Images'}
                    </p>
                    <p className="text-gray-600 text-lg">
                      Simulating SROIE OCR processing
                    </p>
                  </label>
                </div>

                {receipts.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-2xl font-bold">Recent Receipts</h3>
                      <button
                        onClick={exportToCSV}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        <Download className="w-4 h-4" />
                        Export CSV
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
                      {receipts.slice(-12).reverse().map(receipt => (
                        <div key={receipt.id} className="border-2 rounded-xl p-5 bg-gradient-to-br from-white to-gray-50 hover:shadow-lg transition-all">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <p className="font-bold text-lg text-gray-800">{receipt.store}</p>
                              <p className="text-sm text-gray-500">{new Date(receipt.date).toLocaleDateString()}</p>
                            </div>
                            <span className="text-2xl font-bold text-green-600">
                              ${receipt.total}
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                              {receipt.category}
                            </span>
                            <span className="text-sm text-gray-600 font-medium">
                              {receipt.items.length} items
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'summary' && (
              <div className="space-y-8">
                <div className="flex gap-4 mb-6">
                  <div className="flex-1">
                    <label className="block text-sm font-bold mb-2">Select Month</label>
                    <input
                      type="month"
                      value={selectedMonth}
                      onChange={(e) => setSelectedMonth(e.target.value)}
                      className="w-full px-4 py-3 border-2 rounded-xl"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-bold mb-2">Monthly Budget</label>
                    <input
                      type="number"
                      value={budgetLimit}
                      onChange={(e) => setBudgetLimit(parseFloat(e.target.value))}
                      className="w-full px-4 py-3 border-2 rounded-xl"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-2xl p-8 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-emerald-100 font-semibold">Total Spending</p>
                      <DollarSign className="w-10 h-10" />
                    </div>
                    <p className="text-5xl font-bold mb-2">${getTotalSpending()}</p>
                  </div>
                  
                  <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-8 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-blue-100 font-semibold">Receipts</p>
                      <Calendar className="w-10 h-10" />
                    </div>
                    <p className="text-5xl font-bold mb-2">{getMonthlyData().length}</p>
                  </div>
                  
                  <div className="bg-gradient-to-br from-violet-500 to-violet-600 rounded-2xl p-8 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-violet-100 font-semibold">Budget Left</p>
                      <PieChart className="w-10 h-10" />
                    </div>
                    <p className="text-5xl font-bold mb-2">
                      ${Math.max(0, budgetLimit - parseFloat(getTotalSpending())).toFixed(2)}
                    </p>
                  </div>
                </div>

                {getAlerts().length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-2xl font-bold">Alerts</h3>
                    {getAlerts().map((alert, i) => (
                      <div
                        key={i}
                        className={'p-5 rounded-xl flex items-center gap-4 ' + (
                          alert.type === 'danger' ? 'bg-red-50 text-red-800 border-2 border-red-200' :
                          alert.type === 'warning' ? 'bg-yellow-50 text-yellow-800 border-2 border-yellow-200' :
                          alert.type === 'success' ? 'bg-green-50 text-green-800 border-2 border-green-200' :
                          'bg-blue-50 text-blue-800 border-2 border-blue-200'
                        )}
                      >
                        <AlertCircle className="w-6 h-6" />
                        <span className="font-semibold">{alert.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                {getTopStores().length > 0 && (
                  <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-2xl font-bold mb-6">Top 5 Stores</h3>
                    <div className="space-y-4">
                      {getTopStores().map((store, i) => (
                        <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                          <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                              {i + 1}
                            </div>
                            <span className="font-semibold text-lg">{store.store}</span>
                          </div>
                          <span className="text-2xl font-bold text-blue-600">${store.amount.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-8">
                <h2 className="text-3xl font-bold">Spending Analytics</h2>
                
                {getCategoryBreakdown().length > 0 ? (
                  <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                      <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                        <h3 className="text-xl font-bold mb-6">Category Distribution</h3>
                        <ResponsiveContainer width="100%" height={350}>
                          <RechartsPie>
                            <Pie
                              data={getCategoryBreakdown()}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ name, percent }) => name + ' ' + (percent * 100).toFixed(0) + '%'}
                              outerRadius={120}
                              fill="#8884d8"
                              dataKey="value"
                            >
                              {getCategoryBreakdown().map((entry, index) => (
                                <Cell key={'cell-' + index} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </RechartsPie>
                        </ResponsiveContainer>
                      </div>

                      <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                        <h3 className="text-xl font-bold mb-6">Category Breakdown</h3>
                        <ResponsiveContainer width="100%" height={350}>
                          <BarChart data={getCategoryBreakdown()}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="value" fill="#3b82f6" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                      <h3 className="text-xl font-bold mb-6">Daily Spending</h3>
                      <ResponsiveContainer width="100%" height={350}>
                        <AreaChart data={getDailySpending()}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip />
                          <Area type="monotone" dataKey="amount" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                      <h3 className="text-xl font-bold mb-6">Monthly Trend</h3>
                      <ResponsiveContainer width="100%" height={350}>
                        <LineChart data={getAllMonthsData()}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="month" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="total" stroke="#f59e0b" strokeWidth={3} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-20 bg-gray-50 rounded-2xl">
                    <p className="text-xl text-gray-500">No data available</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'reports' && (
              <div className="space-y-8">
                <div className="flex items-center justify-between">
                  <h2 className="text-3xl font-bold">Visual Reports</h2>
                  <button
                    onClick={exportToCSV}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
                  >
                    <Download className="w-5 h-5" />
                    Export Report
                  </button>
                </div>

                {getCategoryBreakdown().length > 0 && (
                  <div className="bg-white border-2 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-bold mb-6">Summary Table</h3>
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-semibold">Category</th>
                          <th className="px-4 py-3 text-right font-semibold">Amount</th>
                          <th className="px-4 py-3 text-right font-semibold">Percentage</th>
                        </tr>
                      </thead>
                      <tbody>
                        {getCategoryBreakdown().map((cat, i) => (
                          <tr key={i} className="border-t hover:bg-gray-50">
                            <td className="px-4 py-3">{cat.name}</td>
                            <td className="px-4 py-3 text-right font-semibold">
                              ${cat.value.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {((cat.value / parseFloat(getTotalSpending())) * 100).toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReceiptExpenseTracker;