let search = () => 
{
    const query = document.getElementById('search-query').value;
    const serachig_elements = document.getElementsByClassName("search-item");

    [...serachig_elements].map((el) =>
    {
        el.style.display = el.textContent.includes(query) ? "block" : "none";

    })
};