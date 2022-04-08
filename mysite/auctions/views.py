from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required

from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
import datetime

# Create your views here.


from .models import User, Auction, Comment, Watchlist
from .forms import AuctionForm, CommentForm, BidForm


def index(request):
    auctions = Auction.objects.all()
    context = {
        'auctions': auctions,
    }
    return render(request, "auctions/index.html", context)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required(login_url='login')
def createlisting(request):

    username = request.user.get_username()
    user_object = User.objects.get(username=username)
    print("The user object is: ", user_object)

    if request.method == 'POST':
        auction_form = AuctionForm(request.POST)

        if auction_form.is_valid():
            new_auction = auction_form.save()
            new_auction.user = user_object
            new_auction.save()
            pk = new_auction.id

            return redirect("listing", pk=pk)

        else:
            # Redirect back to the same page if the data
            # was invalid
            return render(request, "auctions/createlisting.html", {'form': auction_form})

    else:
        auction_form = AuctionForm()
        context = {
            'form': auction_form
        }
        return render(request, "auctions/createlisting.html", context)


def listing(request, pk):

    #Check if auction date has expired and updated it
    check_auction_date(pk)

    # This gets the obj of the current auction
    auction_listing = Auction.objects.get(id=pk)
    comments = auction_listing.comment_set.all()

    if request.user.is_authenticated:

        username = request.user.get_username()
        user = User.objects.get(username=username)

        # User will either post a bid offer or will post comment.
        if request.method == 'POST':

            # Save bid offer (need to check if the bid was higher than highest bid. )
            bid_form = BidForm(request.POST)
            if bid_form.is_valid():
                print("Bid form is valid and form was submitted.")
                user_bid = bid_form.save(commit=False)
                user_bid.auction = auction_listing
                user_bid.user = user
                if user_bid.price >= auction_listing.price and user_bid.price > auction_listing.highest_bid:
                    print("User bid is higher than reserve and highest bid")
                    auction_listing.highest_bid = user_bid.price
                    auction_listing.highest_bidder = username
                    auction_listing.save()
                    user_bid.save()
                else:
                    messages.error(
                        request, "The bid you submitted was not high enough.")

                return redirect("listing", pk=pk)

            # Save comments
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                print("Comments are valid and form was submitted")
                user_comment = comment_form.save( )
                user_comment.auction = auction_listing
                user_comment.user = user
                user_comment.save()

                return redirect("listing", pk=pk)

        else:

            user_watchlist = Watchlist.objects.filter(
                user=(request.user).id, auction=auction_listing.id)

            bid_form = BidForm()

            comment_form = CommentForm()

            context = {
                'listing': auction_listing,
                'user': user,
                'comments': comments,
                'comment_form': comment_form,
                'bid_form': bid_form,
                'user_watchlist': user_watchlist
            }

            return render(request, "auctions/listing.html", context)

    else:

        context = {
              'listing': auction_listing,
                'comments': comments,
              }

        return render(request, "auctions/listing.html", context)


@login_required(login_url='login')
def watchlist(request):

    if request.method == 'POST':

        listing_id = request.POST["listing_id"]
        listing = Auction.objects.get(id=listing_id)

        print("The listing id is:", listing_id)
        print("The listing is:", listing)

        if request.POST["to_watchlist"] == "add_to_watchlist":

            new_to_watch = Watchlist(auction=listing, user=(request.user))
            new_to_watch.save()

        elif request.POST["to_watchlist"] == "remove_from_watchlist":
            # Get the model objects id and then delete.
            delete_from_watchlist = Watchlist.objects.get(
                auction=listing, user=(request.user))

            print("the object to delete is: ", delete_from_watchlist)

            delete_from_watchlist.delete()

        auctions = get_auctions_in_watchlist(request)

        context = {
            'auctions': auctions,
        }

        return render(request, "auctions/watchlist.html", context)

    else:

        auctions = get_auctions_in_watchlist(request)

        context = {
            'auctions': auctions,
        }

        return render(request, "auctions/watchlist.html", context)


def get_auctions_in_watchlist(request):

    # Get all auctions from auctions in users watchlist.

    user_watchlist = Watchlist.objects.filter(user=(request.user).id)

    auction_ids = []

    for item in user_watchlist:
        auction_ids.append(item.auction_id)

        auctions = Auction.objects.filter(id__in=auction_ids)

        return auctions


def closelisting(request):

    if request.method == 'POST':
        pk = request.POST["listing_id"]
        
        # Close the acution
        
        auction = Auction.objects.get(id=pk)
        auction.status = "Closed"
        auction.save()

        return redirect("listing", pk=pk)



def check_auction_date(pk):
    auction_listing = Auction.objects.get(id=pk)
    if auction_listing.status == "Open":
        if datetime.date.today() > auction_listing.end_date:
            # Close the acution
            auction = Auction.objects.get(id=pk)
            auction.status = "Closed"
            auction.save()
