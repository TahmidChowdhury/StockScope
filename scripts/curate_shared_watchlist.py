"""Apply the selected companies to the Shared research list without fetching data."""
from sqlalchemy import delete

from backend.db.models import Company, Watchlist, WatchlistItem
from backend.db.repository import SHARED_COMPANIES
from backend.services.research import repository


def apply(repo):
    with repo.session_factory.begin() as session:
        watchlist = repo._upsert(session, Watchlist, ["name"], {"name": "Shared research", "scope": "shared"})
        ids = []
        for symbol, name in SHARED_COMPANIES.items():
            company = repo._upsert(session, Company, ["symbol"], {"symbol": symbol, "name": name})
            ids.append(company.id)
            repo._upsert(session, WatchlistItem, ["watchlist_id", "company_id"],
                         {"watchlist_id": watchlist.id, "company_id": company.id})
        session.execute(delete(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id, WatchlistItem.company_id.not_in(ids)))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env")
    repo = repository()
    if repo is None:
        raise SystemExit("A configured workspace database is required.")
    apply(repo)
    print("Shared research:", ", ".join(repo.list_symbols()))
