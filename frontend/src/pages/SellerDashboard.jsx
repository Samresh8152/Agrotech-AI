import { useState, useEffect } from 'react'
import { LuWheat, LuSprout, LuTractor, LuFlaskConical } from 'react-icons/lu'
import api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

const CATS = ['crops', 'seeds', 'equipment', 'fertilizer']

export default function SellerDashboard() {
  const { user } = useAuth()

  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    title: '',
    description: '',
    category: 'crops',
    price: '',
    quantity: '',
    unit: 'kg',
    location: '',
  })

  const fetchMyProducts = async () => {
    try {
      const { data } = await api.get('/marketplace/my-products')

      if (data.success) {
        setProducts(data.products)
      }
    } catch (error) {
      toast.error(
        error.response?.data?.message || 'Failed to load products'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMyProducts()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()

    setSubmitting(true)

    try {
      const payload = {
        ...form,
        price: Number(form.price),
        quantity: Number(form.quantity),
      }

      const { data } = await api.post(
        '/marketplace/products',
        payload
      )

      if (data.success) {
        toast.success('Product listed')

        setProducts((previousProducts) => [
          data.product,
          ...previousProducts,
        ])

        setShowForm(false)

        setForm({
          title: '',
          description: '',
          category: 'crops',
          price: '',
          quantity: '',
          unit: 'kg',
          location: '',
        })
      } else {
        toast.error(data.message || 'Failed to create listing')
      }
    } catch (error) {
      toast.error(
        error.response?.data?.message ||
          'Failed to create listing'
      )
    } finally {
      setSubmitting(false)
    }
  }

  const toggleActive = async (product) => {
    try {
      await api.put(
        `/marketplace/products/${product.id}`,
        {
          is_active: !product.is_active,
        }
      )

      setProducts((previousProducts) =>
        previousProducts.map((item) =>
          item.id === product.id
            ? {
                ...item,
                is_active: !item.is_active,
              }
            : item
        )
      )

      toast.success(
        product.is_active
          ? 'Listing deactivated'
          : 'Listing reactivated'
      )
    } catch (error) {
      toast.error(
        error.response?.data?.message || 'Update failed'
      )
    }
  }

  const deleteProduct = async (id) => {
    try {
      await api.delete(`/marketplace/products/${id}`)

      setProducts((previousProducts) =>
        previousProducts.filter((product) => product.id !== id)
      )

      toast.success('Listing removed')
    } catch (error) {
      toast.error(
        error.response?.data?.message || 'Delete failed'
      )
    }
  }

  const inventoryValue = products.reduce(
    (total, product) =>
      total +
      Number(product.price || 0) *
        Number(product.quantity || 0),
    0
  )

  const stats = [
    {
      icon: '',
      value: products.length,
      label: 'Total Listings',
    },
    {
      icon: '',
      value: products.filter((product) => product.is_active).length,
      label: 'Active',
    },
    {
      icon: '',
      value: products.filter((product) => !product.is_active).length,
      label: 'Inactive',
    },
    {
      icon: '',
      value: `₹${inventoryValue.toLocaleString('en-IN')}`,
      label: 'Inventory Value',
    },
  ]

  return (
    <div className="page-container fade-in">
      {/* Page Header */}
      <div className="page-header">

        <div>
          <h1 className="page-title">Seller Dashboard</h1>

          <p className="page-subtitle">
            Manage your product listings on the marketplace
          </p>

          {user?.name && (
            <p
              style={{
                color: 'var(--text-muted)',
                marginTop: '6px',
              }}
            >
              Welcome, {user.name}
            </p>
          )}
        </div>
      </div>

      {/* Statistics */}
      <div
        className="stats-grid"
        style={{ marginBottom: '24px' }}
      >
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="glass-card stat-card"
          >
            <div className="stat-icon">{stat.icon}</div>

            <div className="stat-value">{stat.value}</div>

            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Add Product Button */}
      <div style={{ marginBottom: '20px' }}>
        <button
          className="btn btn-primary"
          onClick={() => setShowForm((previous) => !previous)}
        >
          {showForm ? 'Cancel' : '+ Add New Listing'}
        </button>
      </div>

      {/* Create Product Form */}
      {showForm && (
        <div
          className="glass-card fade-in"
          style={{
            padding: '28px',
            marginBottom: '24px',
          }}
        >
          <h3
            style={{
              fontWeight: 700,
              marginBottom: '20px',
              color: 'var(--text-secondary)',
            }}
          >
            New Product Listing
          </h3>

          <form onSubmit={handleCreate}>
            {/* Product Title */}
            <div className="form-group">
              <label className="form-label">
                Product Title
              </label>

              <input
                className="form-input"
                type="text"
                value={form.title}
                onChange={(e) =>
                  setForm({
                    ...form,
                    title: e.target.value,
                  })
                }
                placeholder="e.g. Organic Wheat Seeds HD-2967"
                required
              />
            </div>

            {/* Description */}
            <div className="form-group">
              <label className="form-label">
                Description
              </label>

              <textarea
                className="form-textarea"
                value={form.description}
                onChange={(e) =>
                  setForm({
                    ...form,
                    description: e.target.value,
                  })
                }
                placeholder="Describe your product..."
                style={{ minHeight: '80px' }}
              />
            </div>

            {/* Category and Unit */}
            <div className="input-row">
              <div className="form-group">
                <label className="form-label">
                  Category
                </label>

                <select
                  className="form-select"
                  value={form.category}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      category: e.target.value,
                    })
                  }
                >
                  {CATS.map((category) => (
                    <option
                      key={category}
                      value={category}
                    >
                      {category.charAt(0).toUpperCase() +
                        category.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Unit
                </label>

                <select
                  className="form-select"
                  value={form.unit}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      unit: e.target.value,
                    })
                  }
                >
                  {[
                    'kg',
                    'quintal',
                    'tonne',
                    'litre',
                    'unit',
                    'bag (50kg)',
                    'bag (25kg)',
                  ].map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Price and Quantity */}
            <div className="input-row">
              <div className="form-group">
                <label className="form-label">
                  Price (₹ per unit)
                </label>

                <input
                  className="form-input"
                  type="number"
                  value={form.price}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      price: e.target.value,
                    })
                  }
                  min="0"
                  step="0.01"
                  placeholder="Enter price"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Available Quantity
                </label>

                <input
                  className="form-input"
                  type="number"
                  value={form.quantity}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      quantity: e.target.value,
                    })
                  }
                  min="0"
                  step="1"
                  placeholder="Enter quantity"
                  required
                />
              </div>
            </div>

            {/* Location */}
            <div className="form-group">
              <label className="form-label">
                Location
              </label>

              <input
                className="form-input"
                type="text"
                value={form.location}
                onChange={(e) =>
                  setForm({
                    ...form,
                    location: e.target.value,
                  })
                }
                placeholder="e.g. Ludhiana, Punjab"
              />
            </div>

            {/* Submit */}
            <button
              className="btn btn-primary"
              type="submit"
              disabled={submitting}
              style={{ justifyContent: 'center' }}
            >
              {submitting
                ? 'Listing...'
                : 'List Product'}
            </button>
          </form>
        </div>
      )}

      {/* Product Listings */}
      {loading ? (
        <div className="loading-screen">
          <div className="spinner" />
          <p>Loading products...</p>
        </div>
      ) : products.length === 0 ? (
        <div
          className="glass-card"
          style={{
            padding: '48px',
            textAlign: 'center',
            color: 'var(--text-muted)',
          }}
        >
          <div
            style={{
              fontSize: '3rem',
              marginBottom: '12px',
            }}
          >
            
          </div>

          <h3 style={{ marginBottom: '8px' }}>
            No Listings Yet
          </h3>

          <p>
            Click "Add New Listing" to start selling your
            agricultural products!
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          {products.map((product) => (
            <div
              key={product.id}
              className="glass-card"
              style={{
                padding: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
              }}
            >
              {/* Product Icon */}
              <div
                style={{
                  width: 52,
                  height: 52,
                  background:
                    'var(--earth-tint)',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--earth)',
                  flexShrink: 0,
                }}
              >
                {product.category === 'crops'
                  ? <LuWheat size={22} />
                  : product.category === 'seeds'
                  ? <LuSprout size={22} />
                  : product.category === 'equipment'
                  ? <LuTractor size={22} />
                  : <LuFlaskConical size={22} />}
              </div>

              {/* Product Details */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    marginBottom: '4px',
                  }}
                >
                  <h3
                    style={{
                      fontWeight: 700,
                      fontSize: '1rem',
                    }}
                  >
                    {product.title}
                  </h3>

                  <span
                    className={`badge ${
                      product.is_active
                        ? 'badge-success'
                        : 'badge-danger'
                    }`}
                  >
                    {product.is_active
                      ? 'Active'
                      : 'Inactive'}
                  </span>
                </div>

                {product.description && (
                  <p
                    style={{
                      fontSize: '0.85rem',
                      color: 'var(--text-muted)',
                      marginBottom: '6px',
                    }}
                  >
                    {product.description}
                  </p>
                )}

                <p
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  ₹
                  {Number(product.price || 0).toLocaleString(
                    'en-IN'
                  )}
                  /{product.unit} ·{' '}
                  {product.quantity} {product.unit} available
                  {product.location
                    ? ` · ${product.location}`
                    : ''}
                </p>
              </div>

              {/* Listing Actions */}
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  className={`btn btn-sm ${
                    product.is_active
                      ? 'btn-secondary'
                      : 'btn-primary'
                  }`}
                  onClick={() => toggleActive(product)}
                >
                  {product.is_active
                    ? 'Deactivate'
                    : '▶ Reactivate'}
                </button>

                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => deleteProduct(product.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}