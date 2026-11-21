class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:

        anagrams= defaultdict(list)

        for x in strs:
                anagrams["".join(sorted(x))].append(x)
        return list(anagrams.values())


        