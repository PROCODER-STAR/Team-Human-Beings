async function searchProduct() {
    const query = document.getElementById("search").value.trim();
    const output = document.getElementById("output");

    if (!query) {
        alert("Please enter a product name");
        return;
    }

    output.innerHTML = "Searching products...";
    let products = [];

    /* ---------- API 1: DummyJSON ---------- */
    try {
        const res1 = await fetch(`https://dummyjson.com/products/search?q=${query}`);
        const data1 = await res1.json();
        if (data1.products.length > 0) {
            products.push({
                name: data1.products[0].title,
                price: data1.products[0].price,
                site: "DummyJSON"
            });
        }
    } catch (e) {
        console.log("DummyJSON failed");
    }

    /* ---------- API 2: FakeStoreAPI ---------- */
    try {
        const res2 = await fetch("https://fakestoreapi.com/products");
        const data2 = await res2.json();
        const found2 = data2.find(p =>
            p.title.toLowerCase().includes(query.toLowerCase())
        );
        if (found2) {
            products.push({
                name: found2.title,
                price: found2.price,
                site: "FakeStore"
            });
        }
    } catch (e) {
        console.log("FakeStoreAPI failed");
    }

    /* ---------- API 3: Local Mock Data ---------- */
    const mockProducts = [
        { name: "iphone", price: 899, site: "LocalShop" },
        { name: "laptop", price: 1200, site: "LocalShop" },
        { name: "headphones", price: 99, site: "LocalShop" }
    ];

    const found3 = mockProducts.find(p =>
        p.name.toLowerCase().includes(query.toLowerCase())
    );

    if (found3) products.push(found3);

    displayResults(products);
}

function displayResults(products) {
    const output = document.getElementById("output");

    if (products.length === 0) {
        output.innerHTML = "No product found.";
        return;
    }

    let best = products[0];
    products.forEach(p => {
        if (p.price < best.price) best = p;
    });

    output.innerHTML = "";

    products.forEach(p => {
        output.innerHTML += `
            <p>
                <strong>Product:</strong> ${p.name}<br>
                <strong>Website:</strong> ${p.site}<br>
                <strong>Price:</strong> $${p.price}
            </p>
            <hr>
        `;
    });

    output.innerHTML += `
        <h3>Best Price</h3>
        <p>
            <strong>${best.site}</strong> offers the lowest price:
            <strong>$${best.price}</strong>
        </p>
    `;
}