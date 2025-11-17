#!/usr/bin/env python3
"""
Year-in-Review Generator

Generates a personalized year-in-review summary for an Airbnb user by querying
Viaduct GraphQL endpoints for trips, experiences, reviews, wishlists, and more.

Usage:
    python3 year_in_review.py <userId> [viaductUrl] [year]

Example:
    python3 year_in_review.py 123570621
    python3 year_in_review.py 123570621 https://viaduct-staging.d.musta.ch/graphql 2024
"""

import sys
import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import base64


@dataclass
class TripDetail:
    location: str
    nights: int
    start_date: str


@dataclass
class TripSummary:
    total_trips: int
    total_nights: int
    countries_visited: List[str]
    cities_visited: List[str]
    longest_trip: Optional[TripDetail]
    destinations: List[str]


@dataclass
class ExperienceSummary:
    total_experiences: int
    categories: Dict[str, int]
    cities: List[str]


@dataclass
class ReviewSummary:
    reviews_written: int
    average_rating_given: float
    five_star_reviews: int


@dataclass
class WishlistSummary:
    total_wishlists: int
    total_items_saved: int
    top_destinations: List[str]


@dataclass
class CommunitySummary:
    hosts_connected: int
    messages_exchanged: int


@dataclass
class UserProfileSummary:
    member_since: str
    years_as_member: int
    is_superhost: bool
    is_highly_rated: bool
    positive_review_rate: float


@dataclass
class TravelPersonality:
    personality_type: str
    description: str
    traits: List[str]


@dataclass
class YearInReviewSummary:
    user_id: str
    year: int
    generated_at: str
    user_profile: UserProfileSummary
    trips: TripSummary
    experiences: ExperienceSummary
    reviews: ReviewSummary
    wishlists: WishlistSummary
    community: CommunitySummary
    travel_personality: Optional[TravelPersonality]
    total_distance_km: float
    highlights: List[str]


class ViaductGraphQLClient:
    def __init__(self, viaduct_url: str, user_id: str):
        self.viaduct_url = viaduct_url
        self.user_id = user_id
        self.session = requests.Session()

    def execute_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Viaduct"""
        variables = variables or {}

        headers = {
            "Content-Type": "application/json",
            "x-airbnb-req-userid": self.user_id,
            "x-csrf-without-token": "1",
            "x-airbnb-viaduct-include-metadata": "y"
        }

        payload = {
            "query": query,
            "variables": variables
        }

        response = self.session.post(
            self.viaduct_url,
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"GraphQL request failed with status {response.status_code}: {response.text}"
            )

        data = response.json()

        if "errors" in data:
            print(f"⚠️  GraphQL returned errors:")
            print(json.dumps(data["errors"], indent=2))

        return data


class YearInReviewGenerator:
    def __init__(self, client: ViaductGraphQLClient, user_id: str, year: int):
        self.client = client
        self.user_id = user_id
        self.year = year

    def generate(self) -> YearInReviewSummary:
        """Generate the complete year-in-review summary"""
        print(f"🎉 Generating Year-in-Review for user {self.user_id} for year {self.year}...")

        start_date = f"{self.year}-01-01T00:00:00Z"
        end_date = f"{self.year + 1}-01-01T00:00:00Z"

        # Fetch all data
        user_profile_data = self.fetch_user_profile()
        trip_data = self.fetch_trip_data(start_date, end_date)
        review_data = self.fetch_review_data()
        wishlist_data = self.fetch_wishlist_data()

        # Process data
        user_profile = self.process_user_profile(user_profile_data)
        trips = self.process_trip_data(trip_data)
        experiences = self.process_experience_data(trip_data)
        reviews = self.process_review_data(review_data)
        wishlists = self.process_wishlist_data(wishlist_data)
        community = CommunitySummary(
            hosts_connected=len(trips.destinations),
            messages_exchanged=0  # Would need messaging API
        )

        # Calculate advanced features
        travel_personality = self.calculate_travel_personality(trips, experiences, reviews)
        total_distance = self.calculate_distance_traveled(trips)

        highlights = self.generate_highlights(trips, experiences, reviews, wishlists)

        return YearInReviewSummary(
            user_id=self.user_id,
            year=self.year,
            generated_at=datetime.now().isoformat(),
            user_profile=user_profile,
            trips=trips,
            experiences=experiences,
            reviews=reviews,
            wishlists=wishlists,
            community=community,
            travel_personality=travel_personality,
            total_distance_km=total_distance,
            highlights=highlights
        )

    def fetch_user_profile(self) -> Dict[str, Any]:
        """Fetch user profile data including badges and member info"""
        print("👤 Fetching user profile...")

        query = """
            query GetUserProfile($userId: ID!) {
              node(id: $userId) {
                ... on User {
                  id
                  createdAt
                  isSuperHost
                  highlyRated
                }
              }
            }
        """

        # Convert numeric userId to base64 encoded ID
        encoded_user_id = base64.b64encode(f"User:{self.user_id}".encode()).decode()

        return self.client.execute_query(query, {"userId": encoded_user_id})

    def fetch_trip_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch trip events from Viaduct"""
        print("📍 Fetching trip data...")

        query = """
            query GetUserTrips($userId: String!) {
              trips {
                tripEvents(
                  userId: $userId
                  sortDirection: DESC
                  orderBy: STARTS_AT
                  first: 100
                ) {
                  edges {
                    node {
                      id
                      eventType
                      productType
                      startsAt
                      endsAt
                      city
                      confirmationCode
                      stayReservation {
                        confirmationCode
                        startDate
                        endDate
                        numberOfNights
                        listing {
                          name
                          supplyListing {
                            location {
                              defaultAddress {
                                locality
                                administrativeZone
                                country
                              }
                            }
                          }
                        }
                      }
                      experienceGuestProfile {
                        template {
                          nameOrPlaceholderName
                          cityNative
                          countryName
                          isOnlineExperience
                        }
                        experienceReservation {
                          startsAt
                        }
                      }
                    }
                  }
                }
              }
            }
        """

        variables = {
            "userId": self.user_id
        }

        result = self.client.execute_query(query, variables)

        # Filter trips by date in Python since we can't use duplicate filters
        if result.get("data", {}).get("trips", {}).get("tripEvents"):
            edges = result["data"]["trips"]["tripEvents"].get("edges", [])
            filtered_edges = []
            for edge in edges:
                node = edge.get("node", {})
                starts_at = node.get("startsAt")
                if starts_at:
                    # Check if trip is within date range
                    if start_date <= starts_at <= end_date:
                        filtered_edges.append(edge)
            result["data"]["trips"]["tripEvents"]["edges"] = filtered_edges

        return result

    def fetch_review_data(self) -> Dict[str, Any]:
        """Fetch user reviews from Viaduct"""
        print("⭐ Fetching review data...")

        query = """
            query GetUserReviews($userId: ID!) {
              node(id: $userId) {
                ... on User {
                  reviews(filter: WRITTEN_REVIEWS, first: 100) {
                    edges {
                      node {
                        review {
                          ... on UserProfileReview {
                            id
                            rating
                            createdAt
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
        """

        # Convert numeric userId to base64 encoded ID
        encoded_user_id = base64.b64encode(f"User:{self.user_id}".encode()).decode()

        return self.client.execute_query(query, {"userId": encoded_user_id})

    def fetch_wishlist_data(self) -> Dict[str, Any]:
        """Fetch user wishlists from Viaduct"""
        print("💝 Fetching wishlist data...")

        query = """
            query GetUserWishlists {
              viewer {
                wishlists(first: 50) {
                  edges {
                    node {
                      id
                      name
                      createdAt
                      productCounts {
                        staysCount
                        experiencesCount
                      }
                    }
                  }
                }
              }
            }
        """

        return self.client.execute_query(query)

    def process_user_profile(self, data: Dict[str, Any]) -> UserProfileSummary:
        """Process user profile data into summary statistics"""
        user_node = data.get("data", {}).get("node", {})

        created_at = user_node.get("createdAt", "")
        years_as_member = 0
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                years_as_member = self.year - dt.year
            except:
                pass

        return UserProfileSummary(
            member_since=created_at,
            years_as_member=years_as_member,
            is_superhost=user_node.get("isSuperHost", False),
            is_highly_rated=user_node.get("highlyRated", False),
            positive_review_rate=0.0  # Would need additional query
        )

    def process_trip_data(self, data: Dict[str, Any]) -> TripSummary:
        """Process trip data into summary statistics"""
        edges = data.get("data", {}).get("trips", {}).get("tripEvents", {}).get("edges", [])

        total_nights = 0
        countries = set()
        cities = set()
        longest_trip = None
        max_nights = 0

        for edge in edges:
            node = edge.get("node", {})
            product_type = node.get("productType")

            if product_type == "STAY":
                stay = node.get("stayReservation", {})
                nights = stay.get("numberOfNights", 0)
                total_nights += nights

                listing = stay.get("listing", {})
                location = (listing.get("supplyListing", {})
                           .get("location", {})
                           .get("defaultAddress", {}))

                country = location.get("country")
                city = location.get("locality")

                if country:
                    countries.add(country)
                if city:
                    cities.add(city)

                if nights > max_nights:
                    max_nights = nights
                    longest_trip = TripDetail(
                        location=city or country or "Unknown",
                        nights=nights,
                        start_date=stay.get("startDate", "")
                    )

        return TripSummary(
            total_trips=len(edges),
            total_nights=total_nights,
            countries_visited=sorted(list(countries)),
            cities_visited=sorted(list(cities)),
            longest_trip=longest_trip,
            destinations=sorted(list(cities))
        )

    def process_experience_data(self, data: Dict[str, Any]) -> ExperienceSummary:
        """Process experience data into summary statistics"""
        edges = data.get("data", {}).get("trips", {}).get("tripEvents", {}).get("edges", [])

        cities = set()
        count = 0

        for edge in edges:
            node = edge.get("node", {})
            product_type = node.get("productType")

            if product_type == "EXPERIENCE":
                count += 1
                exp_profile = node.get("experienceGuestProfile", {})
                template = exp_profile.get("template", {})
                city = template.get("cityNative")
                if city:
                    cities.add(city)

        return ExperienceSummary(
            total_experiences=count,
            categories={},  # Would need category data from API
            cities=sorted(list(cities))
        )

    def process_review_data(self, data: Dict[str, Any]) -> ReviewSummary:
        """Process review data into summary statistics"""
        edges = (data.get("data", {})
                .get("node", {})
                .get("reviews", {})
                .get("edges", []))

        if not edges:
            return ReviewSummary(
                reviews_written=0,
                average_rating_given=0.0,
                five_star_reviews=0
            )

        total_rating = 0
        five_stars = 0

        for edge in edges:
            node = edge.get("node", {})
            review = node.get("review", {})
            rating = review.get("rating", 0)
            total_rating += rating
            if rating == 5:
                five_stars += 1

        return ReviewSummary(
            reviews_written=len(edges),
            average_rating_given=total_rating / len(edges) if edges else 0.0,
            five_star_reviews=five_stars
        )

    def process_wishlist_data(self, data: Dict[str, Any]) -> WishlistSummary:
        """Process wishlist data into summary statistics"""
        edges = (data.get("data", {})
                .get("viewer", {})
                .get("wishlists", {})
                .get("edges", []))

        total_items = 0
        wishlist_names = []

        for edge in edges:
            node = edge.get("node", {})
            counts = node.get("productCounts", {})
            total_items += counts.get("staysCount", 0)
            total_items += counts.get("experiencesCount", 0)

            # Collect wishlist names as destinations proxy
            name = node.get("name", "")
            if name:
                wishlist_names.append(name)

        return WishlistSummary(
            total_wishlists=len(edges),
            total_items_saved=total_items,
            top_destinations=wishlist_names[:5]  # Top 5 wishlist names as proxy
        )

    def calculate_travel_personality(
        self,
        trips: TripSummary,
        experiences: ExperienceSummary,
        reviews: ReviewSummary
    ) -> Optional[TravelPersonality]:
        """Calculate travel personality based on patterns"""
        if trips.total_trips == 0:
            return None

        traits = []

        # Determine personality type based on patterns
        avg_nights = trips.total_nights / trips.total_trips if trips.total_trips > 0 else 0

        if avg_nights > 7:
            personality_type = "The Explorer"
            description = "You love long, immersive stays to truly experience each destination"
            traits.append("Extended stays")
        elif avg_nights < 3:
            personality_type = "The Adventurer"
            description = "You're all about variety, hopping between destinations to see it all"
            traits.append("Quick trips")
        else:
            personality_type = "The Balanced Traveler"
            description = "You strike the perfect balance between exploration and relaxation"
            traits.append("Balanced stays")

        # Add experience-based traits
        if experiences.total_experiences > 0:
            exp_per_trip = experiences.total_experiences / trips.total_trips
            if exp_per_trip > 1:
                traits.append("Experience seeker")

        # Add review-based traits
        if reviews.reviews_written >= trips.total_trips:
            traits.append("Community contributor")

        if reviews.average_rating_given >= 4.5:
            traits.append("Positive outlook")

        # Country diversity
        if len(trips.countries_visited) > trips.total_trips * 0.8:
            traits.append("Country hopper")

        return TravelPersonality(
            personality_type=personality_type,
            description=description,
            traits=traits
        )

    def calculate_distance_traveled(self, trips: TripSummary) -> float:
        """Calculate approximate distance traveled between cities"""
        # This is a simplified calculation
        # In a real implementation, we'd use geocoding and distance APIs

        # Rough estimate: assume average 500km between different cities
        num_cities = len(trips.cities_visited)
        if num_cities <= 1:
            return 0.0

        # Estimate total distance based on number of trips and countries
        estimated_distance = num_cities * 500.0  # Base distance per city

        # Add bonus for international travel
        if len(trips.countries_visited) > 1:
            estimated_distance += (len(trips.countries_visited) - 1) * 1000.0

        return round(estimated_distance, 2)

    def generate_highlights(
        self,
        trips: TripSummary,
        experiences: ExperienceSummary,
        reviews: ReviewSummary,
        wishlists: WishlistSummary
    ) -> List[str]:
        """Generate highlight statements based on summary data"""
        highlights = []

        if trips.total_trips > 0:
            highlights.append(
                f"🌍 You explored {len(trips.countries_visited)} countries "
                f"and {len(trips.cities_visited)} cities!"
            )

        if trips.total_nights > 0:
            highlights.append(f"🏠 You spent {trips.total_nights} nights away from home")

        if trips.longest_trip:
            highlights.append(
                f"⏱️  Your longest adventure: {trips.longest_trip.nights} nights "
                f"in {trips.longest_trip.location}"
            )

        if experiences.total_experiences > 0:
            highlights.append(f"🎭 You tried {experiences.total_experiences} unique experiences")

        if reviews.reviews_written > 0:
            highlights.append(
                f"⭐ You wrote {reviews.reviews_written} reviews "
                f"({reviews.five_star_reviews} were 5-star!)"
            )

        if wishlists.total_items_saved > 0:
            highlights.append(
                f"💝 You saved {wishlists.total_items_saved} places to your wishlists "
                f"for future adventures"
            )

        return highlights


def print_summary(summary: YearInReviewSummary):
    """Print a formatted year-in-review summary in wrapped-style cards"""
    width = 70

    def print_card(title: str, content: List[str], emoji: str = ""):
        """Print a single card"""
        print()
        print("┌" + "─" * (width - 2) + "┐")
        title_text = f"{emoji} {title}" if emoji else title
        padding = (width - len(title_text) - 2) // 2
        print("│" + " " * padding + title_text + " " * (width - len(title_text) - padding - 2) + "│")
        print("├" + "─" * (width - 2) + "┤")

        for line in content:
            if len(line) > width - 4:
                # Wrap long lines
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= width - 4:
                        current_line += word + " "
                    else:
                        print("│ " + current_line.ljust(width - 3) + "│")
                        current_line = word + " "
                if current_line:
                    print("│ " + current_line.strip().ljust(width - 3) + "│")
            else:
                print("│ " + line.ljust(width - 3) + "│")

        print("└" + "─" * (width - 2) + "┘")

    # Header
    print()
    print("═" * width)
    print(f"  🎉 YOUR {summary.year} AIRBNB WRAPPED 🎉".center(width))
    print("═" * width)

    # Card 1: Your 2024 by the numbers
    card1_content = [
        f"🏠 {summary.trips.total_trips} trips taken",
        f"🌙 {summary.trips.total_nights} nights away from home",
        f"🌍 {len(summary.trips.countries_visited)} countries explored",
        f"🏙️  {len(summary.trips.cities_visited)} cities discovered",
        f"🎭 {summary.experiences.total_experiences} experiences enjoyed",
        f"⭐ {summary.reviews.reviews_written} reviews shared",
    ]

    if summary.user_profile.is_highly_rated:
        card1_content.append("✨ Highly Rated Guest Badge!")
    if summary.user_profile.is_superhost:
        card1_content.append("🏆 Superhost Status!")

    print_card(f"YOUR {summary.year} BY THE NUMBERS", card1_content, "📊")

    # Card 2: Places you explored
    card2_content = []
    if summary.trips.countries_visited:
        card2_content.append(f"Countries: {', '.join(summary.trips.countries_visited)}")
        card2_content.append("")
    if summary.trips.cities_visited:
        card2_content.append(f"Cities: {', '.join(summary.trips.cities_visited[:5])}")
        if len(summary.trips.cities_visited) > 5:
            card2_content.append(f"...and {len(summary.trips.cities_visited) - 5} more!")
        card2_content.append("")
    if summary.total_distance_km > 0:
        card2_content.append(f"🛫 Estimated distance traveled: {summary.total_distance_km:,.0f} km")
    if summary.trips.longest_trip:
        card2_content.append("")
        card2_content.append(f"Longest adventure: {summary.trips.longest_trip.nights} nights")
        card2_content.append(f"in {summary.trips.longest_trip.location}")

    print_card("PLACES YOU EXPLORED", card2_content, "🗺️")

    # Card 3: Your travel style
    if summary.travel_personality:
        card3_content = [
            f"You are: {summary.travel_personality.personality_type}",
            "",
            summary.travel_personality.description,
            "",
            "Your traits:",
        ]
        for trait in summary.travel_personality.traits:
            card3_content.append(f"  • {trait}")

        print_card("YOUR TRAVEL STYLE", card3_content, "✨")

    # Card 4: Hosts & experiences
    card4_content = [
        f"👥 Connected with {summary.community.hosts_connected} hosts",
        f"🎭 Tried {summary.experiences.total_experiences} unique experiences",
    ]

    if summary.experiences.cities:
        card4_content.append("")
        card4_content.append(f"Experience cities: {', '.join(summary.experiences.cities[:3])}")

    if summary.reviews.reviews_written > 0:
        card4_content.append("")
        card4_content.append(f"⭐ Left {summary.reviews.reviews_written} reviews")
        card4_content.append(f"   ({summary.reviews.five_star_reviews} were 5-star!)")
        card4_content.append(f"   Average rating: {summary.reviews.average_rating_given:.1f}/5.0")

    print_card("HOSTS & EXPERIENCES", card4_content, "🤝")

    # Card 5: Looking ahead (2025 wishlist preview)
    card5_content = [
        f"💝 You have {summary.wishlists.total_wishlists} wishlists",
        f"📍 {summary.wishlists.total_items_saved} places saved for future adventures",
    ]

    if summary.wishlists.top_destinations:
        card5_content.append("")
        card5_content.append("Top destinations on your radar:")
        for dest in summary.wishlists.top_destinations:
            card5_content.append(f"  • {dest}")

    card5_content.append("")
    card5_content.append("Ready to make {year} even more amazing?".format(year=summary.year + 1))

    print_card("LOOKING AHEAD TO 2025", card5_content, "🔮")

    # Member info footer
    print()
    print("─" * width)
    member_text = f"Airbnb member for {summary.user_profile.years_as_member} years"
    print(member_text.center(width))
    print("─" * width)
    print()


def main():
    if len(sys.argv) < 2:
        print("""
Usage: python3 year_in_review.py <userId> [viaductUrl] [year]

Arguments:
  userId       - Airbnb user ID (required)
  viaductUrl   - Viaduct GraphQL endpoint (default: https://viaduct-staging.d.musta.ch/graphql)
  year         - Year for review (default: 2024)

Example:
  python3 year_in_review.py 123570621
  python3 year_in_review.py 123570621 https://viaduct-staging.d.musta.ch/graphql 2024
        """)
        sys.exit(1)

    user_id = sys.argv[1]
    viaduct_url = sys.argv[2] if len(sys.argv) > 2 else "https://viaduct-staging.d.musta.ch/graphql"
    year = int(sys.argv[3]) if len(sys.argv) > 3 else 2024

    print("=" * 70)
    print(f"  🎉 AIRBNB YEAR IN REVIEW {year} 🎉")
    print("=" * 70)
    print()

    try:
        client = ViaductGraphQLClient(viaduct_url, user_id)
        generator = YearInReviewGenerator(client, user_id, year)
        summary = generator.generate()

        print_summary(summary)

        # Also output JSON for programmatic use
        print("📄 JSON OUTPUT:")
        summary_dict = asdict(summary)
        # Convert nested dataclasses to dict if present
        if summary_dict['trips']['longest_trip']:
            summary_dict['trips']['longest_trip'] = asdict(summary.trips.longest_trip)
        if summary_dict.get('travel_personality'):
            summary_dict['travel_personality'] = asdict(summary.travel_personality)
        summary_dict['user_profile'] = asdict(summary.user_profile)
        print(json.dumps(summary_dict, indent=2))

    except Exception as e:
        print(f"❌ Error generating year-in-review: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
